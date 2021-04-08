from functools import partial

import pytest
import trio
from trio.testing import wait_all_tasks_blocked

from trio_util import AsyncValue, compose_values

async def test_compose_values(nursery):
    async_x = AsyncValue(42)
    async_y = AsyncValue(0)
    done = trio.Event()

    @nursery.start_soon
    async def _wait():
        with compose_values(x=async_x, y=async_y) as composite:
            assert (composite.value.x, composite.value.y) == (42, 0)
            assert await composite.wait_value(lambda val: val.x < 0 < val.y) == (-1, 10)
        done.set()

    await wait_all_tasks_blocked()
    async_x.value = -1
    await wait_all_tasks_blocked()
    async_x.value = 0
    async_y.value = 5
    await wait_all_tasks_blocked()
    async_y.value = 10
    async_x.value = -1  # match (-1, 10) should be captured
    await done.wait()


@pytest.mark.parametrize('context', [
    compose_values,
    partial(compose_values, AsyncValue(0)),
    partial(compose_values, x=10),
])
async def test_compose_values_wrong_usage(context):
    with pytest.raises(TypeError):
        with context():
            pass


async def test_compose_values_nested(nursery):
    async_x, async_y = AsyncValue(1), AsyncValue(2)
    async_text = AsyncValue('foo')
    done = trio.Event()

    @nursery.start_soon
    async def _wait():
        with compose_values(x=async_x, y=async_y) as async_xy, \
                compose_values(xy=async_xy, text=async_text) as composite:
            assert composite.value == ((1, 2), 'foo')
            assert await composite.wait_value(
                lambda val: val.xy.x < 0 < val.xy.y and val.text == 'bar') == ((-1, 10), 'bar')
        done.set()

    await wait_all_tasks_blocked()
    async_x.value = -1
    async_y.value = 10
    await wait_all_tasks_blocked()
    async_text.value = 'bar'
    await wait_all_tasks_blocked()
    await done.wait()


async def test_compose_values_transform():
    async_x = AsyncValue(42)
    async_y = AsyncValue(2)

    with compose_values(x=async_x, y=async_y,
                        _transform_=lambda val: val.x * val.y) as composite:
        assert composite.value == 84
        async_y.value = 10
        assert composite.value == 420


async def test_compose_values_fast_transition():
    # Confirm that composed values are not subject to issues with missed
    # wakeups.  This is true because the implementation relays value changes
    # synchronously from the value setter.
    event = AsyncValue(0)
    N = 5

    with compose_values(e=event) as composite:
        async def _listener(expected):
            await composite.wait_value(expected)

        async with trio.open_nursery() as nursery:
            for i in range(N):
                nursery.start_soon(_listener, (i+1,))
            await wait_all_tasks_blocked()
            # mutate value several times in one scheduler frame
            for i in range(N):
                event.value += 1
        # all listeners exited, so they received their respective events

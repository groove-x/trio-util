import pytest
from trio.testing import assert_checkpoints, wait_all_tasks_blocked

from trio_util import AsyncBool


async def test_bool_event(nursery):
    async def waiter(event: AsyncBool):
        # ensure checkpoint even if condition already true
        assert event.value
        with assert_checkpoints():
            await event.wait_value(True)
        print('#1')
        await event.wait_value(False)
        print('#2')
        await event.wait_transition(True)
        print('#3')
        await event.wait_transition(False)
        print('#4')
        await event.wait_transition(True)
        assert event.value is False
        print('#5')

    x = AsyncBool()
    assert not x.value
    x.value = True
    assert x.value

    y = AsyncBool(True)
    assert y.value

    # 1 (value already true)
    nursery.start_soon(waiter, y)
    await wait_all_tasks_blocked()
    # 2 (level changes to false)
    y.value = False
    await wait_all_tasks_blocked()
    # 3 (transition to true)
    y.value = True
    await wait_all_tasks_blocked()
    # 4 (transition to false)
    y.value = False
    # 5 (transition to true and immediately back to false)
    # Show that wait is triggered even though the value changes again before
    # waiter receives control.
    y.value = True
    y.value = False
    await wait_all_tasks_blocked()


def test_bad_value():
    # confirm we disallow non-bool values
    x = AsyncBool()
    with pytest.raises(TypeError):
        x.value = None


def test_bad_init_value():
    with pytest.raises(TypeError):
        AsyncBool(None)


async def test_bad_wait_value():
    # confirm we disallow non-bool arguments to wait_value/transition()--
    # especially lambda, which can happen due to confusion with AsyncValue API
    x = AsyncBool()
    with pytest.raises(TypeError):
        await x.wait_value(lambda: True)
    with pytest.raises(TypeError):
        await x.wait_transition(lambda: True)


def test_numpy_bool_value():
    # confirm we allow numpy's non-bool bool type
    numpy = pytest.importorskip('numpy')
    x = AsyncBool()
    x.value = numpy.bool_(True)


async def test_wait_transition_any(nursery):
    async def listener(event: AsyncBool):
        assert not event.value
        await event.wait_transition()
        assert event.value
        await event.wait_transition()
        assert not event.value

    x = AsyncBool()
    nursery.start_soon(listener, x)
    await wait_all_tasks_blocked()

    x.value = True
    await wait_all_tasks_blocked()
    x.value = False
    await wait_all_tasks_blocked()

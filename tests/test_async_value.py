from functools import partial
from unittest.mock import Mock

import pytest
import trio
from trio.testing import assert_checkpoints, wait_all_tasks_blocked

from trio_util import AsyncValue
from trio_util._async_value import _ValueWrapper


async def test_value_event(nursery):
    async def waiter(event: AsyncValue):
        # ensure checkpoint even if condition already true
        assert event.value == 20
        with assert_checkpoints():
            assert await event.wait_value(lambda x: x == 20) == 20
        print('#1')
        assert await event.wait_value(lambda x: x > 20) == 21
        print('#2')
        # (test default predicate)
        assert await event.wait_transition() == (30, 21)
        print('#3')
        assert await event.wait_transition(
            lambda val, old: val is None and old is not None) == (None, 30)
        print('#4')
        assert await event.wait_value(lambda x: x > 50) == 51
        await wait_all_tasks_blocked()
        assert event.value == 0
        print('#5')

    foo = AsyncValue(10)
    assert foo.value == 10
    foo.value = 20
    assert foo.value == 20

    # 1 (predicate x == 20 already true)
    nursery.start_soon(waiter, foo)
    await wait_all_tasks_blocked()
    # 2 (predicate x > 20)
    foo.value = 21
    await wait_all_tasks_blocked()
    # 3 (any transition)
    foo.value = 30
    await wait_all_tasks_blocked()
    # 4 (predicate "transition to None" satisfied)
    # Also confirms that None is not special.
    foo.value = None
    # 5 (predicate x > 50 satisfied, then immediately change value)
    # Show that wait is triggered with value satisfying the predicate,
    # even though the value changes again before waiter receives control.
    foo.value = 51
    foo.value = 0
    await wait_all_tasks_blocked()


async def test_wait_value_held_for(nursery, autojump_clock):
    test1_done = trio.Event()
    test2_done = trio.Event()

    async def listener(event: AsyncValue):
        assert event.value == 10  # condition already true
        t0 = trio.current_time()
        assert await event.wait_value(lambda x: x == 10, held_for=1) == 10
        assert trio.current_time() - t0 == 1
        test1_done.set()

        assert event.value < 20  # condition not yet true
        t0 = trio.current_time()
        assert await event.wait_value(lambda x: x >= 20, held_for=1) == 22
        assert trio.current_time() - t0 == 1.5
        test2_done.set()

    x = AsyncValue(10)
    nursery.start_soon(listener, x)
    await test1_done.wait()

    x.value = 20
    await trio.sleep(.25)
    x.value = 5
    await trio.sleep(.25)
    x.value = 22
    await test2_done.wait()


@pytest.mark.parametrize('wait_function, predicate_return', [
    (AsyncValue.wait_value, False),
    (partial(AsyncValue.wait_value, held_for=1), True),
    (AsyncValue.wait_transition, False),
])
async def test_predicate_eval_scope(wait_function, predicate_return, nursery):
    # predicate evaluations are not expected outside of wait_* method lifetime
    x = AsyncValue(0)
    predicate = Mock(return_value=predicate_return)
    cancel_scope = trio.CancelScope()

    @nursery.start_soon
    async def _wait():
        with cancel_scope:
            await wait_function(x, predicate)

    await wait_all_tasks_blocked()
    predicate_call_count = predicate.call_count
    cancel_scope.cancel()
    await wait_all_tasks_blocked()
    x.value = 10
    assert predicate.call_count == predicate_call_count


async def test_wait_value_by_value(nursery):
    done = trio.Event()

    async def listener(event: AsyncValue):
        assert event.value == 10
        assert await event.wait_value(10) == 10
        assert await event.wait_value(12) == 12
        done.set()

    x = AsyncValue(10)
    nursery.start_soon(listener, x)
    await wait_all_tasks_blocked()
    x.value = 12
    await done.wait()


async def test_wait_transition_by_value(nursery):
    done = trio.Event()

    async def listener(event: AsyncValue):
        assert event.value == 10
        assert await event.wait_transition(10) == (10, 9)
        done.set()

    x = AsyncValue(10)
    nursery.start_soon(listener, x)
    await wait_all_tasks_blocked()
    assert not done.is_set()
    x.value = 9
    x.value = 10
    await done.wait()


def _always_false(val):
    return False


@pytest.mark.parametrize('initial_val, wait_val, expected_queue_key_types', [
    # event already set to desired value, so no wait queue
    ('foo', 'foo', []),
    # listeners waiting for the same value, so wait queue is shared
    ('foo', 'bar', [_ValueWrapper]),
    (False, True, [_ValueWrapper]),
    # unhashable value requires a wait queue per listener
    (None, {}, [_ValueWrapper, _ValueWrapper]),
    # (same) predicate will be keyed by the function object
    (None, _always_false, [type(_always_false)]),
])
async def test_wait_queue(initial_val, wait_val, expected_queue_key_types, nursery):
    # two tasks run wait_value() on the same value, check wait queue key type and number

    async def listener(event: AsyncValue):
        assert event.value == initial_val
        await event.wait_value(wait_val)

    x = AsyncValue(initial_val)
    nursery.start_soon(listener, x)
    nursery.start_soon(listener, x)
    await wait_all_tasks_blocked()
    assert [type(val) for val in x._level_results] == expected_queue_key_types

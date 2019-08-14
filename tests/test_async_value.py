from trio.testing import assert_checkpoints, wait_all_tasks_blocked

from trio_util import AsyncValue


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

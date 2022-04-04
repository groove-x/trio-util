from functools import partial
from typing import Optional
from unittest.mock import Mock

import pytest
import trio
from trio.testing import assert_checkpoints, wait_all_tasks_blocked

from trio_util import AsyncValue
from trio_util._async_value import _ValueWrapper


async def test_async_value(nursery):
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

    foo: AsyncValue[Optional[int]] = AsyncValue(10)
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


def test_repr():
    foo = AsyncValue(10)
    assert repr(foo) == 'AsyncValue(10)'


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


def _even(v):
    return v & 1 == 0


def _odd(v):
    return v & 1 == 1


@pytest.mark.parametrize('predicate, held_for, consume_duration, '
                         'publish_durations, expected_values', [
    # fast consumer
    (None,  0, 0.0, [.1] * 3, [0, 1, 2, 3]),
    (_even, 0, 0.0, [.1] * 6, [0, 2, 4, 6]),
    (_odd,  0, 0.0, [.1] * 6, [1, 3, 5]),  # (initial value doesn't match)
    # consumer is a little slower (1s vs .9s), but no lost value
    (None,  0, 1.0, [.9] * 3, [0, 1, 2, 3]),
    # slow consumer misses a change
    (None,  0, 1.0, [.4] * 3, [0, 2, 3]),

    # held_for
    # NOTE: the test harness waits indefinitely for the last expected value
    (_even, 0.5, 0.0, [.9] * 6, [0, 2, 4, 6]),
    (_even, 0.5, 0.0, [.4] * 2 + [.9] * 4, [2, 4, 6]),
    (_even, 0.5, 0.0, [.4, .9] * 3, [6]),
    (_even, 0.5, 0.0, [.9, .4] * 3, [0, 2, 4, 6]),
])
async def test_eventual_values(predicate, held_for,
                               consume_duration, publish_durations, expected_values,
                               nursery, autojump_clock):
    assert held_for == 0 or predicate is not None
    expected_values = expected_values[:]
    x = AsyncValue(0)  # publisher uses sequence [0, 1, 2, ...]
    done_event = trio.Event()

    @nursery.start_soon
    async def _consumer():
        iterator = x.eventual_values() if predicate is None \
                else x.eventual_values(predicate, held_for=held_for)
        async for val in iterator:
            assert expected_values, f'unexpected additional value: {val}'
            assert val == expected_values.pop(0)
            if consume_duration is not None:
                await trio.sleep(consume_duration)
            if not expected_values:
                done_event.set()

    await wait_all_tasks_blocked()
    for duration in publish_durations:
        if duration is not None:
            await trio.sleep(duration)
        x.value += 1
    await done_event.wait()


async def test_eventual_values_aba(nursery, autojump_clock):
    x = AsyncValue(0)  # publisher uses sequence [0, 1, 0, 1, ...]
    done_event = trio.Event()

    # ABA while consumer blocked does not yield a value (by design)
    # https://en.wikipedia.org/wiki/ABA_problem
    consume_duration = 1
    publish_durations = [.1] * 4
    expected_values = [0]

    @nursery.start_soon
    async def _consumer():
        async for val in x.eventual_values():
            assert val == expected_values.pop(0)
            await trio.sleep(consume_duration)
            if not expected_values:
                done_event.set()

    await wait_all_tasks_blocked()
    for duration in publish_durations:
        await trio.sleep(duration)
        x.value ^= 1
    await done_event.wait()


@pytest.mark.parametrize('consume_duration, publish_durations, expected_values', [
    # fast consumer
    (0.0, [.1] * 3, [(1, 0), (2, 1), (3, 2)]),
    # consumer is a little slower (1s vs .9s), so middle transition lost
    (1.0, [.9] * 3, [(1, 0), (3, 2)]),
    # force lost transition due to multiple transitions before subscriber body is entered
    (0.0, [.1, .1, None, .1], [(1, 0), (2, 1), (4, 3)]),
])
async def test_transitions(consume_duration, publish_durations, expected_values,
                           nursery, autojump_clock):
    x = AsyncValue(0)
    done_event = trio.Event()

    @nursery.start_soon
    async def _consumer():
        async for val, old in x.transitions():
            assert (val, old) == expected_values.pop(0)
            await trio.sleep(consume_duration)
            if not expected_values:
                done_event.set()

    await wait_all_tasks_blocked()
    for duration in publish_durations:
        x.value += 1
        if duration is not None:
            await trio.sleep(duration)
    await done_event.wait()


async def test_transitions_parallel_consumers(autojump_clock):

    async def _consumer(agen, expected, done):
        async for val, old in agen:
            assert (val, old) == expected.pop(0)
            if not expected:
                done.set()

    x = AsyncValue(0)
    done_events = []
    unique_predicates = 0

    async with trio.open_nursery() as nursery:
        # listener A - all transitions
        done_events.append(trio.Event())
        nursery.start_soon(_consumer,
                           x.transitions(),
                           [(1, 0), (2, 1), (3, 2), (4, 3)],
                           done_events[-1])
        unique_predicates += 1

        # listener B & C - selective transitions (identical)
        for _ in range(2):
            done_events.append(trio.Event())
            nursery.start_soon(_consumer,
                               x.transitions(2),
                               [(2, 1)],
                               done_events[-1])
        unique_predicates += 1

        await wait_all_tasks_blocked()
        # emit values slowly, subscriber can keep up
        for _ in range(4):
            x.value += 1
            await trio.sleep(.1)
        for event in done_events:
            await event.wait()
        assert len(x._edge_results) == unique_predicates
        nursery.cancel_scope.cancel()

    assert not x._edge_results


def test_open_transform():
    x = AsyncValue(1)

    with x.open_transform(lambda val: val * 2) as y:
        assert y.value == 2
        x.value = 10
        assert y.value == 20

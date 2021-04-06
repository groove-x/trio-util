import pytest
import trio
from trio.testing import wait_all_tasks_blocked

from trio_util import RepeatedEvent


async def test_repeated_event_wait(nursery, autojump_clock):
    done = trio.Event()
    event = RepeatedEvent()

    event.set()
    with pytest.raises(trio.TooSlowError):
        with trio.fail_after(1):
            await event.wait()

    @nursery.start_soon
    async def _listener():
        await event.wait()
        done.set()

    await wait_all_tasks_blocked()
    event.set()
    await done.wait()


async def test_repeated_event_unqueued(nursery, autojump_clock):
    event = RepeatedEvent()
    counts = [0, 0]

    # a set() before the listener opens will not be queued
    event.set()

    async def listener(i):
        async for _ in event.unqueued_events():
            counts[i] += 1
            await trio.sleep(i + 1)

    for i_ in range(2):
        nursery.start_soon(listener, i_)
    await wait_all_tasks_blocked()
    assert counts == [0, 0]

    event.set()
    await wait_all_tasks_blocked()
    assert counts == [1, 1]

    # this set() is ignored by 2nd listener since it's still in the loop
    await trio.sleep(1.5)
    event.set()
    await wait_all_tasks_blocked()
    assert counts == [2, 1]

    # 1st listener misses this set()
    await trio.sleep(.9)
    event.set()
    await trio.sleep(4)
    assert counts == [2, 2]


async def test_repeated_event_eventually_consistent(nursery, autojump_clock):
    event = RepeatedEvent()
    counts = [0, 0]

    # a set() before the listener opens will not be queued
    event.set()

    async def listener(i):
        async for _ in event.events():
            counts[i] += 1
            await trio.sleep(i + 1)

    for i_ in range(2):
        nursery.start_soon(listener, i_)
    await wait_all_tasks_blocked()
    assert counts == [0, 0]

    event.set()
    await wait_all_tasks_blocked()
    assert counts == [1, 1]

    # 2nd listener is blocked during this set()
    await trio.sleep(1.5)
    event.set()
    await wait_all_tasks_blocked()
    assert counts == [2, 1]
    await trio.sleep(.6)
    assert counts == [2, 2]

    # both listeners blocked during this set()
    event.set()
    await wait_all_tasks_blocked()
    assert counts == [2, 2]
    await trio.sleep(3)
    assert counts == [3, 3]


async def test_repeated_event_repeat_last(autojump_clock):
    event = RepeatedEvent()

    # no event was set, repeat_last=True will still iterate immediately
    async for _ in event.events(repeat_last=True):
        break

    # set between listener sessions is missed
    event.set()
    with pytest.raises(trio.TooSlowError):
        with trio.fail_after(1):
            async for _ in event.events():
                break

    # repeat_last=True will still iterate immediately
    async for _ in event.events(repeat_last=True):
        break

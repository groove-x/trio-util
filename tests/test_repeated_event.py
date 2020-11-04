import pytest
import trio
from trio.testing import wait_all_tasks_blocked

from trio_util import UnqueuedRepeatedEvent, MailboxRepeatedEvent


async def test_unqueued_repeated_event(nursery, autojump_clock):
    event = UnqueuedRepeatedEvent()
    counts = [0, 0]

    # a set() before the listener opens will not be queued
    event.set()

    async def listener(i):
        async for _ in event:
            counts[i] += 1
            await trio.sleep(i + 1)

    for i in range(2):
        nursery.start_soon(listener, i)
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


async def test_mailbox_repeated_event(nursery, autojump_clock):
    event = MailboxRepeatedEvent()
    count = 0

    # this set() will be queued since there is no listener
    event.set()

    @nursery.start_soon
    async def _listener():
        async for _ in event:
            nonlocal count
            count += 1
            await trio.sleep(1)

    await wait_all_tasks_blocked()
    assert count == 1

    # this set() will be queued since listener is not waiting
    event.set()
    await wait_all_tasks_blocked()
    assert count == 1
    await trio.sleep(2)
    assert count == 2

    # 2nd listener not allowed
    with pytest.raises(RuntimeError):
        async for _ in event:
            pass

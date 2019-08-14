import pytest
import trio
from trio.testing import wait_all_tasks_blocked

from trio_util import UnqueuedRepeatedEvent, MailboxRepeatedEvent


async def test_unqueued_repeated_event(nursery, autojump_clock):
    event = UnqueuedRepeatedEvent()
    count = 0

    # this set() is ignored since there is no listener
    event.set()

    @nursery.start_soon
    async def _listener():
        async for _ in event:
            nonlocal count
            count += 1
            await trio.sleep(1)

    await wait_all_tasks_blocked()
    assert count == 0

    event.set()
    await wait_all_tasks_blocked()
    assert count == 1

    # this set() is ignored since listener is not yet waiting
    event.set()
    await wait_all_tasks_blocked()
    assert count == 1

    await trio.sleep(2)
    event.set()
    await wait_all_tasks_blocked()
    assert count == 2

    # 2nd listener not allowed
    with pytest.raises(RuntimeError):
        async for _ in event:
            pass


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

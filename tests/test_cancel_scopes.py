import trio

from mock import AsyncMock  # type: ignore[attr-defined]

from trio_util import move_on_when


async def test_move_on_when(autojump_clock):
    event = trio.Event()

    async with move_on_when(event.wait) as cancel_scope:
        pass
        # context manager exits normally even if awaitable doesn't return
    assert not cancel_scope.cancel_called
    assert not cancel_scope.cancelled_caught

    set_event = False
    async with move_on_when(event.wait) as cancel_scope:
        await trio.sleep(1)
        assert not event.is_set()
        event.set()
        set_event = True
        await trio.sleep_forever()
    assert set_event
    assert cancel_scope.cancel_called
    assert cancel_scope.cancelled_caught


async def test_move_on_when_deadline(autojump_clock):
    async with move_on_when(trio.sleep_forever) as cancel_scope:
        cancel_scope.deadline = trio.current_time() + 1
        await trio.sleep_forever()
    assert trio.current_time() == 1
    assert cancel_scope.cancel_called
    assert cancel_scope.cancelled_caught


async def test_move_on_when_args():
    fn = AsyncMock()

    async with move_on_when(fn, 'foo', bar=10):
        pass
    fn.assert_awaited_with('foo', bar=10)

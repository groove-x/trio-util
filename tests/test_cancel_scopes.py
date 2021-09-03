import trio

from mock import AsyncMock  # type: ignore[attr-defined]

from trio_util import move_on_when


async def test_move_on_when(autojump_clock):
    event = trio.Event()

    async with move_on_when(event.wait) as cancel_scope:
        assert isinstance(cancel_scope, trio.CancelScope)
        # context manager exits normally even if awaitable doesn't return

    set_event = False
    async with move_on_when(event.wait):
        await trio.sleep(1)
        assert not event.is_set()
        event.set()
        set_event = True
        await trio.sleep_forever()
    assert set_event


async def test_move_on_when_args():
    fn = AsyncMock()

    async with move_on_when(fn, 'foo', bar=10):
        pass
    fn.assert_awaited_with('foo', bar=10)

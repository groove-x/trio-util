import pytest
import trio

from trio_util import defer_to_cancelled


async def test_defer_to_cancelled_simple_exception():
    with pytest.raises(ValueError):
        with defer_to_cancelled(ValueError):
            raise ValueError


async def test_defer_to_cancelled_simple_cancel():
    with trio.move_on_after(1) as cancel_scope:
        with defer_to_cancelled(ValueError):
            cancel_scope.cancel()
            await trio.sleep(0)


async def test_defer_to_cancelled_deferred():
    with pytest.raises(trio.Cancelled):
        with defer_to_cancelled(ValueError):
            raise trio.MultiError([trio.Cancelled._create(), ValueError()])


async def test_defer_to_cancelled_deferred_multiple():
    with pytest.raises(trio.Cancelled):
        with defer_to_cancelled(ValueError, KeyError):
            raise trio.MultiError([trio.Cancelled._create(), ValueError(),
                                   KeyError()])


async def test_defer_to_cancelled_not_deferred():
    with pytest.raises(trio.MultiError):
        with defer_to_cancelled(ValueError):
            raise trio.MultiError([trio.Cancelled._create(), KeyError()])


async def test_defer_to_cancelled_decorating_async():
    @defer_to_cancelled(ValueError)
    async def foo():
        raise trio.MultiError([trio.Cancelled._create(), ValueError()])

    with pytest.raises(trio.Cancelled):
        await foo()

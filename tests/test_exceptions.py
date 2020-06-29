import pytest
import trio

from trio_util import defer_to_cancelled, multi_error_defer_to


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


async def test_defer_to_cancelled_deferred_nested_multi_error():
    with pytest.raises(trio.Cancelled):
        with defer_to_cancelled(ValueError):
            raise trio.MultiError([
                ValueError(),
                trio.MultiError([trio.Cancelled._create(), trio.Cancelled._create()])
            ])


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


# TODO: parameterize tests

async def test_multi_error_defer_simple_exception():
    with pytest.raises(ValueError):
        with multi_error_defer_to(trio.Cancelled, ValueError):
            raise ValueError


async def test_multi_error_defer_simple_cancel():
    with trio.move_on_after(1) as cancel_scope:
        with multi_error_defer_to(trio.Cancelled, ValueError):
            cancel_scope.cancel()
            await trio.sleep(0)


async def test_multi_error_defer():
    with pytest.raises(trio.Cancelled):
        with multi_error_defer_to(trio.Cancelled, ValueError):
            raise trio.MultiError([trio.Cancelled._create(), ValueError()])


async def test_multi_error_defer_nested():
    with pytest.raises(trio.Cancelled):
        with multi_error_defer_to(trio.Cancelled, ValueError):
            raise trio.MultiError([
                ValueError(),
                trio.MultiError([trio.Cancelled._create(), trio.Cancelled._create()])
            ])


async def test_multi_error_defer_derived():
    class MyExceptionBase(Exception):
        pass
    class MyException(MyExceptionBase):
        pass
    with pytest.raises(MyException):
        with multi_error_defer_to(MyExceptionBase, trio.Cancelled):
            raise trio.MultiError([trio.Cancelled._create(), MyException()])


async def test_multi_error_defer_deferred_same_repr_strict():
    with pytest.raises(ValueError):
        with multi_error_defer_to(ValueError, trio.Cancelled):
            raise trio.MultiError([ValueError(), ValueError(), trio.Cancelled._create()])


async def test_multi_error_defer_deferred_different_repr_strict():
    with pytest.raises(trio.MultiError):
        with multi_error_defer_to(ValueError, trio.Cancelled):
            raise trio.MultiError([ValueError('foo'), ValueError('bar'), trio.Cancelled._create()])


async def test_multi_error_defer_deferred_different_repr_strict_no_propagate():
    with pytest.raises(RuntimeError):
        with multi_error_defer_to(ValueError, trio.Cancelled, propagate_multi_error=False):
            raise trio.MultiError([ValueError('foo'), ValueError('bar'), trio.Cancelled._create()])


async def test_multi_error_defer_deferred_different_repr_no_strict():
    with pytest.raises(ValueError):
        with multi_error_defer_to(ValueError, trio.Cancelled, strict=False):
            raise trio.MultiError([ValueError('foo'), ValueError('bar'), trio.Cancelled._create()])


async def test_multi_error_defer_no_match():
    with pytest.raises(trio.MultiError):
        with multi_error_defer_to(trio.Cancelled, ValueError):
            raise trio.MultiError([trio.Cancelled._create(), KeyError()])


async def test_multi_error_defer_no_match_no_propagate():
    with pytest.raises(RuntimeError):
        with multi_error_defer_to(trio.Cancelled, ValueError, propagate_multi_error=False):
            raise trio.MultiError([trio.Cancelled._create(), KeyError()])


async def test_multi_error_defer_decorating_async():
    @multi_error_defer_to(trio.Cancelled, ValueError)
    async def foo():
        raise trio.MultiError([trio.Cancelled._create(), ValueError()])

    with pytest.raises(trio.Cancelled):
        await foo()

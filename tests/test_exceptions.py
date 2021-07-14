import pytest
import trio

from trio_util import defer_to_cancelled, multi_error_defer_to


def _cancelled():
    return trio.Cancelled._create()  # type: ignore[attr-defined]


class MyExceptionBase(Exception):
    pass


class MyException(MyExceptionBase):
    pass


@pytest.mark.parametrize("context, to_raise, expected_exception", [
    # simple exception
    (defer_to_cancelled(ValueError),
     ValueError,
     ValueError),
    # MultiError gets deferred
    (defer_to_cancelled(ValueError),
     trio.MultiError([_cancelled(), ValueError()]),
     trio.Cancelled),
    # multiple exception types
    (defer_to_cancelled(ValueError, KeyError),
     trio.MultiError([_cancelled(), ValueError(), KeyError()]),
     trio.Cancelled),
    # nested MultiError
    (defer_to_cancelled(ValueError),
     trio.MultiError([
         ValueError(),
         trio.MultiError([_cancelled(), _cancelled()])
     ]),
     trio.Cancelled),
    # non-matching exception
    (defer_to_cancelled(ValueError),
     trio.MultiError([_cancelled(), KeyError()]),
     trio.MultiError),
])
async def test_defer_to_cancelled(context, to_raise, expected_exception):
    with pytest.raises(expected_exception):
        with context:
            raise to_raise


async def test_defer_to_cancelled_simple_cancel():
    with trio.move_on_after(1) as cancel_scope:
        with defer_to_cancelled(ValueError):
            cancel_scope.cancel()
            await trio.sleep(0)


async def test_defer_to_cancelled_decorating_async():
    @defer_to_cancelled(ValueError)
    async def foo():
        raise trio.MultiError([_cancelled(), ValueError()])

    with pytest.raises(trio.Cancelled):
        await foo()


async def test_defer_to_cancelled_decorating_sync():
    @defer_to_cancelled(ValueError)
    def foo():
        raise trio.MultiError([_cancelled(), ValueError()])

    with pytest.raises(trio.Cancelled):
        foo()


@pytest.mark.parametrize("context, to_raise, expected_exception", [
    # simple exception
    (multi_error_defer_to(trio.Cancelled, ValueError),
     ValueError,
     ValueError),
    # MultiError
    (multi_error_defer_to(trio.Cancelled, ValueError),
     trio.MultiError([_cancelled(), ValueError()]),
     trio.Cancelled),
    # nested MultiError
    (multi_error_defer_to(trio.Cancelled, ValueError),
     trio.MultiError([
         ValueError(),
         trio.MultiError([_cancelled(), _cancelled()])
     ]),
     trio.Cancelled),
    # exception subclass
    (multi_error_defer_to(MyExceptionBase, trio.Cancelled),
     trio.MultiError([_cancelled(), MyException()]),
     MyException),
    # exception objects with same repr are grouped
    (multi_error_defer_to(ValueError, trio.Cancelled),
     trio.MultiError([ValueError(), ValueError(), _cancelled()]),
     ValueError),
    # exception objects with different repr are not grouped
    (multi_error_defer_to(ValueError, trio.Cancelled),
     trio.MultiError([ValueError('foo'), ValueError('bar'), _cancelled()]),
     trio.MultiError),
    # MultiError propagation disallowed
    (multi_error_defer_to(ValueError, trio.Cancelled, propagate_multi_error=False),
     trio.MultiError([ValueError('foo'), ValueError('bar'), _cancelled()]),
     RuntimeError),
    # grouping of exception instances with different repr allowed
    (multi_error_defer_to(ValueError, trio.Cancelled, strict=False),
     trio.MultiError([ValueError('foo'), ValueError('bar'), _cancelled()]),
     ValueError),
    # no matching exception
    (multi_error_defer_to(trio.Cancelled, ValueError),
     trio.MultiError([_cancelled(), KeyError()]),
     trio.MultiError),
    # no matching exception, propagation disallowed
    (multi_error_defer_to(trio.Cancelled, ValueError, propagate_multi_error=False),
     trio.MultiError([_cancelled(), KeyError()]),
     RuntimeError),
])
async def test_multi_error_defer_to(context, to_raise, expected_exception):
    with pytest.raises(expected_exception):
        with context:
            raise to_raise


async def test_multi_error_defer_simple_cancel():
    with trio.move_on_after(1) as cancel_scope:
        with multi_error_defer_to(trio.Cancelled, ValueError):
            cancel_scope.cancel()
            await trio.sleep(0)


async def test_multi_error_defer_decorating_async():
    @multi_error_defer_to(trio.Cancelled, ValueError)
    async def foo():
        raise trio.MultiError([_cancelled(), ValueError()])

    with pytest.raises(trio.Cancelled):
        await foo()

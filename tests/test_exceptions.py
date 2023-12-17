import sys

import pytest
import trio

from trio_util import defer_to_cancelled, exceptgroup_defer_to

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup, BaseExceptionGroup


def _cancelled() -> trio.Cancelled:
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
     BaseExceptionGroup('', [_cancelled(), ValueError()]),
     trio.Cancelled),
    # multiple exception types
    (defer_to_cancelled(ValueError, KeyError),
     BaseExceptionGroup('', [_cancelled(), ValueError(), KeyError()]),
     trio.Cancelled),
    # nested MultiError
    (defer_to_cancelled(ValueError),
     BaseExceptionGroup('', [
         ValueError(),
         BaseExceptionGroup('', [_cancelled(), _cancelled()])
     ]),
     trio.Cancelled),
    # non-matching exception
    (defer_to_cancelled(ValueError),
     BaseExceptionGroup('', [_cancelled(), KeyError()]),
     BaseExceptionGroup),
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
        raise BaseExceptionGroup('', [_cancelled(), ValueError()])

    with pytest.raises(trio.Cancelled):
        await foo()


async def test_defer_to_cancelled_decorating_sync():
    @defer_to_cancelled(ValueError)
    def foo():
        raise BaseExceptionGroup('', [_cancelled(), ValueError()])

    with pytest.raises(trio.Cancelled):
        foo()


@pytest.mark.parametrize("context, to_raise, expected_exception", [
    # simple exception
    (exceptgroup_defer_to(trio.Cancelled, ValueError),
     ValueError,
     ValueError),
    # MultiError
    (exceptgroup_defer_to(trio.Cancelled, ValueError),
     BaseExceptionGroup('', [_cancelled(), ValueError()]),
     trio.Cancelled),
    # nested MultiError
    (exceptgroup_defer_to(trio.Cancelled, ValueError),
     BaseExceptionGroup('', [
         ValueError(),
         BaseExceptionGroup('', [_cancelled(), _cancelled()])
     ]),
     trio.Cancelled),
    # exception subclass
    (exceptgroup_defer_to(MyExceptionBase, trio.Cancelled),
     BaseExceptionGroup('', [_cancelled(), MyException()]),
     MyException),
    # exception objects with same repr are grouped
    (exceptgroup_defer_to(ValueError, trio.Cancelled),
     BaseExceptionGroup('', [ValueError(), ValueError(), _cancelled()]),
     ValueError),
    # exception objects with different repr are not grouped
    (exceptgroup_defer_to(ValueError, trio.Cancelled),
     BaseExceptionGroup('', [ValueError('foo'), ValueError('bar'), _cancelled()]),
     BaseExceptionGroup),
    # MultiError propagation disallowed
    (exceptgroup_defer_to(ValueError, trio.Cancelled, propagate_exc_group=False),
     BaseExceptionGroup('', [ValueError('foo'), ValueError('bar'), _cancelled()]),
     RuntimeError),
    # grouping of exception instances with different repr allowed
    (exceptgroup_defer_to(ValueError, trio.Cancelled, strict=False),
     BaseExceptionGroup('', [ValueError('foo'), ValueError('bar'), _cancelled()]),
     ValueError),
    # no matching exception
    (exceptgroup_defer_to(trio.Cancelled, ValueError),
     BaseExceptionGroup('', [_cancelled(), KeyError()]),
     BaseExceptionGroup),
    # no matching exception, propagation disallowed
    (exceptgroup_defer_to(trio.Cancelled, ValueError, propagate_exc_group=False),
     BaseExceptionGroup('', [_cancelled(), KeyError()]),
     RuntimeError),
])
async def test_exceptgroup_defer_to(context, to_raise, expected_exception):
    with pytest.raises(expected_exception):
        with context:
            raise to_raise


async def test_multi_error_defer_simple_cancel():
    with trio.move_on_after(1) as cancel_scope:
        with exceptgroup_defer_to(trio.Cancelled, ValueError):
            cancel_scope.cancel()
            await trio.sleep(0)


async def test_multi_error_defer_decorating_async():
    @exceptgroup_defer_to(trio.Cancelled, ValueError)
    async def foo():
        raise BaseExceptionGroup('', [_cancelled(), ValueError()])

    with pytest.raises(trio.Cancelled):
        await foo()

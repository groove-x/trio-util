from collections import defaultdict
from contextlib import _GeneratorContextManager
from functools import wraps
from inspect import iscoroutinefunction
from typing import Type, Dict, List

import trio


class _AsyncFriendlyGeneratorContextManager(_GeneratorContextManager):
    """
    Hack contextlib._GeneratorContextManager so that resulting context
    manager can properly decorate async functions.
    """

    def __call__(self, func):
        if iscoroutinefunction(func):
            @wraps(func)
            async def inner(*args, **kwargs):
                with self._recreate_cm():  # type: ignore[attr-defined]
                    return await func(*args, **kwargs)
        else:
            @wraps(func)
            def inner(*args, **kwargs):
                with self._recreate_cm():  # type: ignore[attr-defined]
                    return func(*args, **kwargs)
        return inner


def _async_friendly_contextmanager(func):
    """
    Equivalent to @contextmanager, except the resulting (non-async) context
    manager works correctly as a decorator on async functions.
    """
    @wraps(func)
    def helper(*args, **kwargs):
        return _AsyncFriendlyGeneratorContextManager(func, args, kwargs)
    return helper


def defer_to_cancelled(*args: Type[Exception]):
    """Context manager which defers MultiError exceptions to Cancelled.

    In the scope of this context manager, any raised trio.MultiError exception
    which is a combination of the given exception types and trio.Cancelled
    will have the exception types filtered, leaving only a Cancelled exception.

    The intended use is where routine exceptions (e.g. which are part of an API)
    might occur simultaneously with Cancelled (e.g. when using move_on_after()).
    Without properly catching and filtering the resulting MultiError, an
    unhandled exception will occur.  Often what is desired in this case is
    for the Cancelled exception alone to propagate to the cancel scope.

    Equivalent to ``multi_error_defer_to(trio.Cancelled, *args)``.

    :param args:  One or more exception types which will defer to
        trio.Cancelled.  By default, all exception types will be filtered.

    Example::

        # If MultiError([Cancelled, Obstacle]) occurs, propagate only Cancelled
        # to the parent cancel scope.
        with defer_to_cancelled(Obstacle):
            try:
                # async call which may raise exception as part of API
                await advance(speed)
            except Obstacle:
                # handle API exception (unless Cancelled raised simultaneously)
                ...
    """
    return multi_error_defer_to(trio.Cancelled, *args)


@_async_friendly_contextmanager
def multi_error_defer_to(*privileged_types: Type[BaseException],
                         propagate_multi_error=True,
                         strict=True):
    """
    Defer a trio.MultiError exception to a single, privileged exception

    In the scope of this context manager, a raised MultiError will be coalesced
    into a single exception with the highest privilege if the following
    criteria is met:

        1. every exception in the MultiError is an instance of one of the given
           privileged types

    additionally, by default with strict=True:

        2. there is a single candidate at the highest privilege after grouping
           the exceptions by repr().  For example, this test fails if both
           ValueError('foo') and ValueError('bar') are the most privileged.

    If the criteria are not met, by default the original MultiError is
    propagated.  Use propagate_multi_error=False to instead raise a
    RuntimeError in these cases.

    Examples::

        multi_error_defer_to(trio.Cancelled, MyException)
            MultiError([Cancelled(), MyException()]) -> Cancelled()
            MultiError([Cancelled(), MyException(),
                        MultiError([Cancelled(), Cancelled())]]) -> Cancelled()
            MultiError([Cancelled(), MyException(), ValueError()]) -> *no change*
            MultiError([MyException('foo'), MyException('foo')]) -> MyException('foo')
            MultiError([MyException('foo'), MyException('bar')]) -> *no change*

        multi_error_defer_to(MyImportantException, trio.Cancelled, MyBaseException)
            # where isinstance(MyDerivedException, MyBaseException)
            #   and isinstance(MyImportantException, MyBaseException)
            MultiError([Cancelled(), MyDerivedException()]) -> Cancelled()
            MultiError([MyImportantException(), Cancelled()]) -> MyImportantException()

    :param privileged_types: exception types from highest priority to lowest
    :param propagate_multi_error: if false, raise a RuntimeError where a
        MultiError would otherwise be leaked
    :param strict: propagate MultiError if there are multiple output exceptions
        to chose from (i.e. multiple exceptions objects with differing repr()
        are instances of the privileged type).  When combined with
        propagate_multi_error=False, this case will raise a RuntimeError.
    """
    try:
        yield
    except trio.MultiError as root_multi_error:
        # flatten the exceptions in the MultiError, grouping by repr()
        multi_errors = [root_multi_error]
        errors_by_repr = {}  # exception_repr -> exception_object
        while multi_errors:
            multi_error = multi_errors.pop()
            for e in multi_error.exceptions:
                if isinstance(e, trio.MultiError):
                    multi_errors.append(e)
                    continue
                if not isinstance(e, privileged_types):
                    # not in privileged list
                    if propagate_multi_error:
                        raise
                    raise RuntimeError('Unhandled trio.MultiError') from root_multi_error
                errors_by_repr[repr(e)] = e
        # group the resulting errors by index in the privileged type list
        # priority_index -> exception_object
        errors_by_priority: Dict[int, List[BaseException]] = defaultdict(list)
        for e in errors_by_repr.values():
            for priority, privileged_type in enumerate(privileged_types):
                if isinstance(e, privileged_type):
                    errors_by_priority[priority].append(e)
        # the error (or one of the errors) of the most privileged type wins
        priority_errors = errors_by_priority[min(errors_by_priority)]
        if strict and len(priority_errors) > 1:
            # multiple unique exception objects at the same priority
            if propagate_multi_error:
                raise
            raise RuntimeError('Unhandled trio.MultiError') from root_multi_error
        raise priority_errors[0]

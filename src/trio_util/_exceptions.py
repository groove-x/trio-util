from contextlib import _GeneratorContextManager
from functools import wraps
from inspect import iscoroutinefunction
from typing import Type

import trio


class _AsyncFriendlyGeneratorContextManager(_GeneratorContextManager):
    """
    Hack contextlib._GeneratorContextManager so that resulting context
    manager can properly decorate async functions.
    """

    def __call__(self, func):
        if iscoroutinefunction(func):
            wraps(func)
            async def inner(*args, **kwargs):
                with self._recreate_cm():  # pylint: disable=not-context-manager
                    return await func(*args, **kwargs)
        else:
            wraps(func)
            def inner(*args, **kwargs):
                with self._recreate_cm():  # pylint: disable=not-context-manager
                    return func(*args, **kwargs)
        return inner


def async_friendly_contextmanager(func):
    """
    Equivalent to @contextmanager, except the resulting (non-async) context
    manager works correctly as a decorator on async functions.
    """
    @wraps(func)
    def helper(*args, **kwargs):
        return _AsyncFriendlyGeneratorContextManager(func, args, kwargs)
    return helper


@async_friendly_contextmanager
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

    TODO: Support consolidation of simultaneous user API exceptions
        (i.e. MultiError without Cancelled).  This would work by prioritized list
        of exceptions to defer to.  E.g. given::

            [Cancelled, WheelObstruction, RangeObstruction]

        then::

            Cancelled + RangeObstruction => Cancelled
            WheelObstruction + RangeObstruction => WheelObstruction
    """
    try:
        yield
    except trio.MultiError as e:
        exceptions = e.exceptions
        if not any(isinstance(exc, trio.Cancelled) for exc in exceptions):
            raise
        if not args:
            raise trio.MultiError.filter(
                lambda exc: exc if isinstance(exc, trio.Cancelled) else None,
                e)
        raise trio.MultiError.filter(
            lambda exc: None if isinstance(exc, args) else exc,
            e)

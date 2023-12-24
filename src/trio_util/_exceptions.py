import sys
from collections import defaultdict
from contextlib import _GeneratorContextManager
from functools import wraps
from inspect import iscoroutinefunction
from typing import TYPE_CHECKING, Any, Callable, ContextManager, Dict, Iterator, List, Type, TypeVar

import trio

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup

T = TypeVar('T')
CallT = TypeVar('CallT', bound=Callable[..., object])

if TYPE_CHECKING:
    from typing_extensions import ParamSpec, TypeAlias
    ArgsT = ParamSpec('ArgsT')
    _GCM: TypeAlias = _GeneratorContextManager
else:
    # Dummy value to make _GCM[T] work at runtime.
    _GCM = {T: _GeneratorContextManager}


class _AsyncFriendlyGeneratorContextManager(_GCM[T]):
    """
    Hack contextlib._GeneratorContextManager so that resulting context
    manager can properly decorate async functions.
    """

    def __call__(self, func: CallT) -> CallT:
        # We can't type the internals properly - inside the true branch the return type is async,
        # but we can't express that. It needs to be a typevar bound to callable, so that it fully
        # preserves overloads and things like that.
        if iscoroutinefunction(func):
            @wraps(func)
            async def inner(*args: object, **kwargs: object) -> object:
                with self._recreate_cm():  # type: ignore[attr-defined]  # pylint: disable=not-context-manager
                    return await func(*args, **kwargs)
        else:
            @wraps(func)
            def inner(*args: Any, **kwargs: Any) -> Any:
                with self._recreate_cm():  # type: ignore[attr-defined]  # pylint: disable=not-context-manager
                    return func(*args, **kwargs)
        return inner  # type: ignore


def _async_friendly_contextmanager(
    func: 'Callable[ArgsT, Iterator[T]]',
) -> 'Callable[ArgsT, ContextManager[T]]':
    """
    Equivalent to @contextmanager, except the resulting (non-async) context
    manager works correctly as a decorator on async functions.
    """
    @wraps(func)
    def helper(*args: 'ArgsT.args', **kwargs: 'ArgsT.kwargs') -> ContextManager[T]:
        return _AsyncFriendlyGeneratorContextManager(func, args, kwargs)
    return helper


def defer_to_cancelled(*args: Type[BaseException]) -> ContextManager[None]:
    """Context manager which defers [Base]ExceptionGroup exceptions to Cancelled.

    In the scope of this context manager, any raised [Base]ExceptionGroup exception
    which is a combination of the given exception types and trio.Cancelled
    will have the exception types filtered, leaving only a Cancelled exception.

    The intended use is where routine exceptions (e.g. which are part of an API)
    might occur simultaneously with Cancelled (e.g. when using move_on_after()).
    Without properly catching and filtering the resulting ExceptionGroup, an
    unhandled exception will occur.  Often what is desired in this case is
    for the Cancelled exception alone to propagate to the cancel scope.

    Equivalent to ``exceptgroup_defer_to(trio.Cancelled, *args)``.

    :param args:  One or more exception types which will defer to
        trio.Cancelled.  By default, all exception types will be filtered.

    Example::

        # If ExceptionGroup([Cancelled, Obstacle]) occurs, propagate only Cancelled
        # to the parent cancel scope.
        with defer_to_cancelled(Obstacle):
            try:
                # async call which may raise exception as part of API
                await advance(speed)
            except Obstacle:
                # handle API exception (unless Cancelled raised simultaneously)
                ...
    """
    return exceptgroup_defer_to(trio.Cancelled, *args)


@_async_friendly_contextmanager
def exceptgroup_defer_to(
    *privileged_types: Type[BaseException],
    propagate_exc_group: bool = True,
    strict: bool = True,
) -> Iterator[None]:
    """
    Defer a [Base]ExceptionGroup exception to a single, privileged exception.

    In the scope of this context manager, a raised ExceptionGroup will be coalesced
    into a single exception with the highest privilege if the following
    criteria is met:

        1. every exception in the ExceptionGroup is an instance of one of the given
           privileged types

    additionally, by default with strict=True:

        2. there is a single candidate at the highest privilege after grouping
           the exceptions by repr().  For example, this test fails if both
           ValueError('foo') and ValueError('bar') are the most privileged.

    If the criteria are not met, by default the original ExceptionGroup is
    propagated.  Use propagate_exc_group=False to instead raise a
    RuntimeError in these cases.

    Examples::

        exceptgroup_defer_to(trio.Cancelled, MyException)
            ExceptionGroup([Cancelled(), MyException()]) -> Cancelled()
            ExceptionGroup([Cancelled(), MyException(),
                        ExceptionGroup([Cancelled(), Cancelled())]]) -> Cancelled()
            ExceptionGroup([Cancelled(), MyException(), ValueError()]) -> *no change*
            ExceptionGroup([MyException('foo'), MyException('foo')]) -> MyException('foo')
            ExceptionGroup([MyException('foo'), MyException('bar')]) -> *no change*

        exceptgroup_defer_to(MyImportantException, trio.Cancelled, MyBaseException)
            # where isinstance(MyDerivedException, MyBaseException)
            #   and isinstance(MyImportantException, MyBaseException)
            ExceptionGroup([Cancelled(), MyDerivedException()]) -> Cancelled()
            ExceptionGroup([MyImportantException(), Cancelled()]) -> MyImportantException()

    :param privileged_types: exception types from highest priority to lowest
    :param propagate_exc_group: if false, raise a RuntimeError where a
        ExceptionGroup would otherwise be leaked
    :param strict: propagate ExceptionGroup if there are multiple output exceptions
        to chose from (i.e. multiple exceptions objects with differing repr()
        are instances of the privileged type).  When combined with
        propagate_exc_group=False, this case will raise a RuntimeError.
    """
    try:
        yield
    except BaseExceptionGroup as root_exc_group:
        # flatten the exceptions in the MultiError, grouping by repr()
        exc_groups = [root_exc_group]
        errors_by_repr = {}  # exception_repr -> exception_object
        while exc_groups:
            exc_group = exc_groups.pop()
            for e in exc_group.exceptions:
                if isinstance(e, BaseExceptionGroup):
                    exc_groups.append(e)
                    continue
                if not isinstance(e, privileged_types):
                    # not in privileged list
                    if propagate_exc_group:
                        raise
                    raise RuntimeError('Unhandled ExceptionGroup') from root_exc_group
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
            if propagate_exc_group:
                raise
            raise RuntimeError('Unhandled ExceptionGroup') from root_exc_group
        raise priority_errors[0]


def multi_error_defer_to(
    *privileged_types: Type[BaseException],
    propagate_multi_error: bool = True,
    strict: bool = True,
) -> ContextManager[None]:
    """Deprecated alias for exceptgroup_defer_to()."""
    import warnings
    warnings.warn(
        'multi_error_defer_to() is deprecated, use exceptgroup_defer_to() instead.',
        DeprecationWarning,
        stacklevel=2,
    )
    return exceptgroup_defer_to(
        *privileged_types,
        propagate_exc_group=propagate_multi_error,
        strict=strict,
    )

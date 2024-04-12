# pylint: disable=line-too-long,multiple-statements
from contextlib import contextmanager
from typing import (
    Any, Generator, Set, TypeVar, Generic, AsyncIterator, Tuple,
    ContextManager, Callable, Union, cast, overload, TYPE_CHECKING,
)

import trio

try:
    from trio import lowlevel
except ImportError:  # pragma: no cover
    from trio import hazmat as lowlevel  # type: ignore

from ._ref_counted_default_dict import _RefCountedDefaultDict

if TYPE_CHECKING:
    from typing_extensions import TypeGuard


class _WaitQueue:
    """Fast replacement for trio.ParkingLot.

    The typical unpark_all() is 2x faster.
    """

    __slots__ = ['tasks']

    def __init__(self) -> None:
        self.tasks: Set[lowlevel.Task] = set()

    async def park(self) -> None:
        task = lowlevel.current_task()
        self.tasks.add(task)

        def abort_fn(_: object) -> lowlevel.Abort:
            self.tasks.remove(task)
            return lowlevel.Abort.SUCCEEDED

        await lowlevel.wait_task_rescheduled(abort_fn)

    def unpark_all(self) -> None:
        for task in self.tasks:
            lowlevel.reschedule(task)
        self.tasks.clear()


def _ANY_TRANSITION(value: object, old_value: object) -> bool:
    return True


def _ANY_VALUE(value: object) -> bool:
    return True


_UNSET: Any = object()
T = TypeVar('T')
T2 = TypeVar('T2')
T3 = TypeVar('T3')
P = Callable[[T], bool]
P2 = Callable[[T, T], bool]
CallT = TypeVar('CallT', bound=Callable[..., object])


class _Result(Generic[T]):
    __slots__ = ['event', 'value']

    def __init__(self) -> None:
        self.event = _WaitQueue()
        self.value: T = _UNSET


# TODO: hash functools.partial by func + args + keywords when possible
class _ValueWrapper:
    """
    If value_or_predicate is not callable, wrap it in a suitable callable, and
    hash by the original value if possible.

    This provides a consistent interface for awaitables, and allows listeners
    of the same plain value to share a wait queue.
    """

    __slots__ = ['value']

    def __new__(cls, value_or_predicate: object) -> Any:
        return value_or_predicate if callable(value_or_predicate) else super().__new__(cls)

    def __init__(self, value: object) -> None:
        self.value = value

    def __hash__(self) -> int:
        try:
            return hash(self.value)
        except TypeError:
            return super().__hash__()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _ValueWrapper):
            return self.value.__eq__(other.value)
        return NotImplemented

    def __call__(self, x: object, *args: object) -> TypeGuard[Any]:
        # Not TypeGuard, but all usages below may have a typeguard passed in.
        return x == self.value


class AsyncValue(Generic[T]):
    """
    Value wrapper offering the ability to wait for a value or transition.

    Synopsis::

        >>> a = AsyncValue(0)  # NOTE: can wrap any type (enum, tuple, ...)
        >>> ...
        >>> a.value = 5   # access underlying value
        >>> ...
        >>> # wait for value match by equality
        >>> await a.wait_value(7)
        >>> ...
        >>> # wait for value match by predicate
        >>> await a.wait_value(lambda v: v > 10)
        >>> ...
        >>> # values via iteration (with eventual consistency)
        >>> async for value a.eventual_values(lambda v: v > 10):
        >>>     ...
        >>> # wait for any transition
        >>> await a.wait_transition()
        >>> ...
        >>> # wait for transition by equality
        >>> await a.wait_transition(14)
        >>> ...
        >>> # wait for transition by predicate
        >>> await a.wait_transition(lambda v, old: v > 10 and old < 0)
        >>> ...
        >>> # repeated transitions via iteration (misses values while blocked)
        >>> async for value, _ in a.transitions(lambda v, old: v > 10 and old < 0):
        >>>     ...

    When using any of the wait methods or iterators in this API, note that
    the value may have changed again before the caller receives control.
    For clarity, the specific value that triggered the wakeup is always
    returned.

    Comparison of eventual_values() and transitions() iterators::

        eventual_values()                      transitions()
        =================                      =============
        • high level & safe                    • low level & requires care
        • evaluated on each value change       • evaluated on each value change
            and when starting loop                 if caller not blocked in the body
        • eventually iterates latest value     • latest value missed if caller is blocked
        • can miss rapid value changes         • can miss rapid value changes
        • condition uses new value only        • condition uses new and/or old value
        • mainly used for sync'ing state       • mainly used for triggering work
        • not subject to user races            • races possible on init and each iteration
                                                   (especially if value changes infrequently)

    Performance note:  assignment to the `value` property typically has O(N)
    complexity, where N is the number of actively waiting tasks.  Shared
    predicates are grouped when possible, reducing N to the number of active
    predicates.
    """
    _value: T
    _level_results: _RefCountedDefaultDict[P[T], _Result[T]]
    _edge_results: _RefCountedDefaultDict[P2[T], _Result[Tuple[T, T]]]
    _transforms: _RefCountedDefaultDict[Callable[[T], Any], 'AsyncValue[Any]']

    def __init__(self, value: T) -> None:
        self._value = value
        self._level_results = _RefCountedDefaultDict(_Result)
        self._edge_results = _RefCountedDefaultDict(_Result)
        # predicate: AsyncValue
        self._transforms = _RefCountedDefaultDict(lambda: AsyncValue(_UNSET))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value})"

    @property
    def value(self) -> T:
        """The wrapped value"""
        return self._value

    @value.setter
    def value(self, x: T) -> None:
        if self._value != x:
            old = self._value
            new = self._value = x
            for f, level_result in self._level_results.items():
                if f(new):
                    level_result.value = new
                    level_result.event.unpark_all()
            for f2, edge_result in self._edge_results.items():
                if f2(new, old):
                    edge_result.value = (new, old)
                    edge_result.event.unpark_all()
            for f3, output in self._transforms.items():
                output.value = f3(new)

    @overload
    @staticmethod
    async def _wait_predicate(
        result_map: _RefCountedDefaultDict[Callable[..., Any], _Result[T2]],
        predicate: Callable[[T2], TypeGuard[T3]],
    ) -> T3: ...
    @overload
    @staticmethod
    async def _wait_predicate(
        result_map: _RefCountedDefaultDict[CallT, _Result[T3]], predicate: CallT,
    ) -> T3: ...
    @staticmethod
    async def _wait_predicate(
        result_map: _RefCountedDefaultDict[Callable[..., Any], _Result[T2]],
        predicate: Callable[..., Any],
    ) -> Any:
        with result_map.open_ref(predicate) as result:
            await result.event.park()
        return result.value

    # The self-type is used here so the return value is always T2, even without a predicate.
    @overload
    async def wait_value(self: 'AsyncValue[T2]', __value: T2, *, held_for: float = 0.0) -> T2: ...
    @overload
    async def wait_value(
        self,
        __predicate: 'Callable[[T], TypeGuard[T2]]', *, held_for: float = 0.0,
    ) -> T2: ...
    @overload
    async def wait_value(self: 'AsyncValue[T2]', __predicate: P[T2], *, held_for: float = 0.0) -> T2: ...
    async def wait_value(
        self, value_or_predicate: Union[T2, P[T2], 'Callable[[T], TypeGuard[T2]]'],
        *,
        held_for: float = 0.0,
    ) -> T2:
        """
        Wait until given predicate f(value) is True.

        The predicate is tested immediately and, if false, whenever
        the `value` property changes.

        If a non-callable is provided, it's equivalent to a predicate matching
        the given value.

        If held_for > 0, the predicate must match for that duration from the
        time of the call.  "held" means that the predicate is continuously true.

        returns value which satisfied the predicate
        (when held_for > 0, it's the most recent value)
        """
        value: T2
        predicate: Callable[[T], TypeGuard[T2]] = _ValueWrapper(value_or_predicate)
        while True:
            if not predicate(self._value):
                value = await self._wait_predicate(self._level_results, predicate)
            else:
                value = self._value
                await trio.sleep(0)
            if held_for > 0:
                with trio.move_on_after(held_for):
                    await self.wait_value(lambda v: not predicate(v))
                    continue
            break
        return value

    # NOTE: it's hard to make both type check and lint happy with generator overloads
    # https://github.com/python/mypy/issues/10301
    # https://github.com/PyCQA/astroid/issues/1015
    # eval() returns Any, so we ignore wrong types.
    # The self-type is used here so the return value is always T2, even without a predicate.
    @overload
    async def eventual_values(
        self: 'AsyncValue[T2]', __value: T2, held_for: float = 0.0,
    ) -> AsyncIterator[T2]: yield eval('')
    @overload
    async def eventual_values(
        self,
        __predicate: 'Callable[[T], TypeGuard[T2]]',
        held_for: float = 0.0,
    ) -> AsyncIterator[T2]: yield eval('')
    @overload
    async def eventual_values(
        self: 'AsyncValue[T2]',
        __predicate: P[T2] = _ANY_VALUE,
        held_for: float = 0.0,
    ) -> AsyncIterator[T2]: yield self._value
    async def eventual_values(
        self,
        value_or_predicate: Union[T2, P[T2], 'Callable[[T], TypeGuard[T2]]'] = _ANY_VALUE,
        held_for: float = 0.0,
    ) -> AsyncIterator[T2]:
        """
        Yield values matching the predicate with eventual consistency

        The initial value will be yielded immediately if it matches the
        predicate.  Subsequent yields occur whenever the `value` property
        changes to a value matching the predicate.  Note that rapid changes as
        well as multiple changes while the caller body is blocked will not all
        be reflected, but eventual consistency is ensured.

        The default predicate will match any value.

        If a non-callable is provided, it's equivalent to a predicate matching
        the given value.

        If held_for > 0, the predicate must match for that duration.
        """
        predicate = _ValueWrapper(value_or_predicate)
        last_value = self._value
        with self._level_results.open_ref(predicate) as result, \
                self._level_results.open_ref(lambda v: v != last_value) as not_last_value, \
                self._level_results.open_ref(lambda v: not predicate(v)) as not_predicate:
            while True:
                if predicate(self._value):
                    last_value = self._value
                else:
                    await result.event.park()
                    last_value = result.value
                if held_for > 0:
                    with trio.move_on_after(held_for):
                        await not_predicate.event.park()
                        continue
                # predicate() has been checked, we know this is the matching value.
                yield last_value  # type: ignore[misc]
                if self._value == last_value:
                    await not_last_value.event.park()

    # TODO: implement wait_transition() using transitions()
    @overload
    async def wait_transition(self, __value: T) -> Tuple[T, T]: ...
    @overload
    async def wait_transition(self, __predicate: P2[T] = _ANY_TRANSITION) -> Tuple[T, T]: ...
    async def wait_transition(self, value_or_predicate: Union[T, P2[T]] = _ANY_TRANSITION) -> Tuple[T, T]:
        """
        Wait until given predicate f(value, old_value) is True.

        The predicate is tested whenever the `value` property changes.
        The default predicate responds to any value change.

        If a non-callable is provided, it's equivalent to a predicate matching
        the given value.

        Note that unlike `wait_value()`, it is easy to have race conditions
        when using `wait_transition()`.  Always consider whether it's possible
        for the initially desired transition to have already occurred due to
        task scheduling order, etc.

        returns (value, old_value) which satisfied the predicate
        """
        value: P2[T] = _ValueWrapper(value_or_predicate)
        return await self._wait_predicate(self._edge_results, value)

    @overload
    async def transitions(self, __value: T) -> AsyncIterator[Tuple[T, T]]: yield (self._value, self._value)
    @overload
    async def transitions(self, __predicate: P2[T] = _ANY_TRANSITION) -> AsyncIterator[Tuple[T, T]]: yield (self._value, self._value)
    async def transitions(self, value_or_predicate: Union[T, P2[T]] = _ANY_TRANSITION) -> AsyncIterator[Tuple[T, T]]:
        """
        Yield (value, old_value) for transitions matching the predicate

        Transitions that happen during the body of the loop are discarded.

        The iteration::

            >>> async for value, old_value in async_value.transitions(...)
            >>>     ...

        is equivalent to::

            >>> while True:
            >>>     value, old_value = await async_value.wait_transition(...)
            >>>     ...

        Unlike the `eventual_values()` iterator, use of the `transitions()` is
        prone to races when entering the loop.  Always consider whether it's
        possible for the desired transition to have already occurred due to
        task scheduling order, etc.
        """

        # Note this is not simply `while True: await wait_transition(...)`,
        # in order to maintain a ref on the predicate throughout the loop.
        predicate = _ValueWrapper(value_or_predicate)
        with self._edge_results.open_ref(predicate) as result:
            while True:
                await result.event.park()
                yield result.value

    # TODO: make the output's `value` read-only somehow
    def open_transform(self, function: Callable[[T], T2]) -> ContextManager['AsyncValue[T2]']:
        """Yield a derived AsyncValue with the given transform applied

        Synopsis::

        >>> x = AsyncValue(1)
        >>> with x.open_transform(lambda val: val * 2) as y:
        >>>     assert y.value == 2
        >>>     x.value = 10
        >>>     assert y.value == 20
        """
        # type hint workaround for https://youtrack.jetbrains.com/issue/PY-36444
        return self._open_transform(function)

    @contextmanager
    def _open_transform(
        self, function: Callable[[T], T2],
    ) -> Generator['AsyncValue[T2]', None, None]:
        output: AsyncValue[T2]
        with self._transforms.open_ref(function) as output:
            if output.value is _UNSET:
                output.value = function(self.value)
            yield output

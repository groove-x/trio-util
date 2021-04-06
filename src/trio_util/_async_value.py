from contextlib import contextmanager

import trio

try:
    from trio.lowlevel import ParkingLot as WaitQueue
except ImportError:
    from trio.hazmat import ParkingLot as WaitQueue

from ._ref_counted_default_dict import _RefCountedDefaultDict


def _ANY_TRANSITION(value, old_value):
    return True


def _ANY_VALUE(value):
    return True


_NONE = object()


class _Result:
    __slots__ = ['event', 'value']

    def __init__(self):
        self.event = WaitQueue()
        self.value = None


# TODO: hash functools.partial by func + args + keywords when possible
class _ValueWrapper:
    """
    If value_or_predicate is not callable, wrap it in a suitable callable, and
    hash by the original value if possible.

    This provides a consistent interface for awaitables, and allows listeners
    of the same plain value to share a wait queue.
    """

    __slots__ = ['value']

    def __new__(cls, value_or_predicate):
        return value_or_predicate if callable(value_or_predicate) else super().__new__(cls)

    def __init__(self, value):
        self.value = value

    def __hash__(self):
        try:
            return hash(self.value)
        except TypeError:
            return super().__hash__()

    def __eq__(self, other):
        return self.value.__eq__(other.value)

    def __call__(self, x, *args):
        return x == self.value


class AsyncValue:
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
        >>> # wait for transition by equality
        >>> await a.wait_transition(14)
        >>> ...
        >>> # wait for transition by predicate (default: any transition)
        >>> await a.wait_transition(lambda v, old: v > 10 and old < 0)
        >>> ...
        >>> # repeated transitions via iteration
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

    def __init__(self, value):
        self._value = value
        self._level_results = _RefCountedDefaultDict(_Result)
        self._edge_results = _RefCountedDefaultDict(_Result)
        # predicate: AsyncValue
        self._transforms = _RefCountedDefaultDict(lambda: AsyncValue(_NONE))

    def __repr__(self):
        return f"{self.__class__.__name__}(value={self.value})"

    @property
    def value(self):
        """The wrapped value"""
        return self._value

    @value.setter
    def value(self, x):
        if self._value != x:
            old = self._value
            new = self._value = x
            for f, result in self._level_results.items():
                if f(new):
                    result.value = new
                    result.event.unpark_all()
            for f, result in self._edge_results.items():
                if f(new, old):
                    result.value = (new, old)
                    result.event.unpark_all()
            for f, output in self._transforms.items():
                output.value = f(new)

    @staticmethod
    async def _wait_predicate(result_map, predicate):
        with result_map.open_ref(predicate) as result:
            await result.event.park()
        return result.value

    async def wait_value(self, value_or_predicate, *, held_for=0):
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
        predicate = _ValueWrapper(value_or_predicate)
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

    async def eventual_values(self, value_or_predicate=_ANY_VALUE):
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
        """
        predicate = _ValueWrapper(value_or_predicate)
        last_value = None
        with self._level_results.open_ref(predicate) as result, \
                self._level_results.open_ref(lambda v: v != last_value) as not_last_value:
            while True:
                if predicate(self._value):
                    last_value = self._value
                else:
                    await result.event.park()
                    last_value = result.value
                yield last_value
                if self._value == last_value:
                    await not_last_value.event.park()

    # TODO: held_for
    # TODO: implement wait_transition() using transitions()
    async def wait_transition(self, value_or_predicate=_ANY_TRANSITION):
        """
        Wait until given predicate f(value, old_value) is True.

        The predicate is tested whenever the `value` property changes.
        The default predicate responds to any value change.

        If a non-callable is provided, it's equivalent to a predicate matching
        the given value.

        returns (value, old_value) which satisfied the predicate
        """
        return await self._wait_predicate(self._edge_results, _ValueWrapper(value_or_predicate))

    async def transitions(self, value_or_predicate=_ANY_TRANSITION):
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
        """

        # Note this is not simply `while True: await wait_transition(...)`,
        # in order to maintain a ref on the predicate throughout the loop.
        predicate = _ValueWrapper(value_or_predicate)
        with self._edge_results.open_ref(predicate) as result:
            while True:
                await result.event.park()
                yield result.value

    @contextmanager
    def open_transform(self, function):
        """Yield a derived AsyncValue with the given transform applied

        Synopsis::

        >>> x = AsyncValue(1)
        >>> with x.open_transform(lambda val: val * 2) as y:
        >>>     assert y.value == 2
        >>>     x.value = 10
        >>>     assert y.value == 20
        """
        # TODO: make the output's `value` read-only somehow
        with self._transforms.open_ref(function) as output:
            if output.value is _NONE:
                output.value = function(self.value)
            yield output

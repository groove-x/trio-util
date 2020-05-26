from collections import defaultdict

import trio

try:
    from trio.lowlevel import ParkingLot as WaitQueue
except ImportError:
    from trio.hazmat import ParkingLot as WaitQueue


def _ANY_TRANSITION(value, old_value):
    return True


class _Result:
    __slots__ = ['event', 'value']

    def __init__(self):
        self.event = WaitQueue()
        self.value = None


class AsyncValue:
    """
    Value wrapper offering the ability to wait for a value or transition.

    Synopsis:
        >>> a = AsyncValue(0)  # NOTE: can wrap any type (enum, tuple, ...)
        >>> ...
        >>> a.value = 5   # access underlying value
        >>> ...
        >>> # wait for value predicate
        >>> await a.wait_value(lambda v: v > 10)
        >>> ...
        >>> # wait for transition predicate (default: any)
        >>> await a.wait_transition(lambda v, old: v > 10 and old < 0)

    When using `wait_value()` and `wait_transition()`, note that the value may
    have changed again before the caller receives control.

    Performance note:  assignment to the `value` property has O(N) complexity,
    where N is the number of active wait predicates.
    """

    def __init__(self, value):
        self._value = value
        self._old = None  # NOTE: initial value is never exposed in API
        self._level_results = defaultdict(_Result)
        self._edge_results = defaultdict(_Result)

    def __repr__(self):
        return f"AsyncValue(value={self.value})"

    @property
    def value(self):
        """The wrapped value"""
        return self._value

    @value.setter
    def value(self, x):
        if self._value != x:
            old = self._old = self._value
            new = self._value = x
            for f, result in list(self._level_results.items()):
                if f(new):
                    result.value = new
                    result.event.unpark_all()
                    del self._level_results[f]
            for f, result in list(self._edge_results.items()):
                if f(new, old):
                    result.value = (new, old)
                    result.event.unpark_all()
                    del self._edge_results[f]

    async def wait_value(self, predicate):
        """
        Wait until given predicate f(value) is True.

        The predicate is tested immediately and, if false, whenever
        the `value` property changes.

        returns value which satisfied the predicate
        """
        if not predicate(self._value):
            result = self._level_results[predicate]
            await result.event.park()
            value = result.value
        else:
            value = self._value
            await trio.sleep(0)
        return value

    async def wait_transition(self, predicate=None):
        """
        Wait until given predicate f(value, old_value) is True.

        The predicate is tested whenever the `value` property changes.
        The default is `None`, which responds to any value change.

        returns (value, old_value) which satisfied the predicate
        """
        result = self._edge_results[predicate or _ANY_TRANSITION]
        await result.event.park()
        return result.value

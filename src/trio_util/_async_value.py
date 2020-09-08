from collections import defaultdict, namedtuple
from contextlib import asynccontextmanager
from functools import partial

import trio

try:
    from trio.lowlevel import ParkingLot as WaitQueue
except ImportError:
    from trio.hazmat import ParkingLot as WaitQueue


def _ANY_TRANSITION(value, old_value):
    return True


class _Result:
    __slots__ = ['event', 'value', 'refs']

    def __init__(self):
        self.event = WaitQueue()
        self.value = None
        self.refs = 0


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

    When using `wait_value()` and `wait_transition()`, note that the value may
    have changed again before the caller receives control.

    Performance note:  assignment to the `value` property has O(N) complexity,
    where N is the number of active wait predicates.
    """

    def __init__(self, value):
        self._value = value
        self._level_results = defaultdict(_Result)
        self._edge_results = defaultdict(_Result)

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
            for f, result in list(self._level_results.items()):
                if f(new):
                    result.value = new
                    result.event.unpark_all()
            for f, result in list(self._edge_results.items()):
                if f(new, old):
                    result.value = (new, old)
                    result.event.unpark_all()

    @staticmethod
    async def _wait_predicate(result_map, predicate):
        result = result_map[predicate]
        result.refs += 1
        try:
            await result.event.park()
        finally:
            result.refs -= 1
            if not result.refs:
                del result_map[predicate]
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

    # TODO: held_for
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


@asynccontextmanager
async def compose_values(**value_map):
    """Async context manager providing a composite of multiple AsyncValues

    The composite object itself is an AsyncValue, with the `value` of each
    underlying object accessible as attributes on the composite `value`.

    `compose_values()` expects named AsyncValue instances to be provided as
    keyword arguments.  The attributes of the composite value will correspond
    to the given names.

    It's mostly an implementation detail, but the composite value type is a
    namedtuple.  Users should not write to the composite `value` attribute
    since it is exclusively managed by the context.

    Synopsis:
        >>> async_x, async_y = AsyncValue(-1), AsyncValue(10)
        >>>
        >>> async with compose_values(x=async_x, y=async_y) as async_xy:
        >>>     result = await async_xy.wait_value(lambda val: val.x < 0 < val.y))
        >>>
        >>> result
        CompositeValue(x=-1, y=10)
    """
    async with trio.open_nursery() as nursery:
        values = value_map.values()
        # the implementation requires `wait_transition()` taking a predicate
        if not (values and all(isinstance(e, AsyncValue) for e in values)):
            raise TypeError('expected instances of AsyncValue')
        value_type = namedtuple('CompositeValue', value_map.keys())
        composite = AsyncValue(value_type._make(e.value for e in values))

        # This predicate is run indefinitely per underlying value and updates
        # the composite as a side effect.
        def _update_composite(name, val, _):
            composite.value = composite.value._replace(**{name: val})
            return False

        for name, e in value_map.items():
            nursery.start_soon(e.wait_transition, partial(_update_composite, name))

        yield composite
        nursery.cancel_scope.cancel()

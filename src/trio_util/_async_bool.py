from collections import defaultdict

import trio

try:
    from trio.lowlevel import ParkingLot as WaitQueue
except ImportError:
    from trio.hazmat import ParkingLot as WaitQueue

try:
    # work around numpy bool madness
    import numpy  # pylint: disable=import-error
    _BOOL_TYPES = (bool, numpy.bool_)
except ModuleNotFoundError:
    _BOOL_TYPES = (bool,)  # type: ignore

_BOOL_OR_NONE_TYPES = _BOOL_TYPES + (type(None), )


class AsyncBool:
    """Boolean wrapper offering the ability to wait for a value or transition.

    Synopsis:
        >>> a = AsyncBool()
        >>> ...
        >>> a.value = True   # access underlying value
        >>> ...
        >>> await a.wait_value(False)  # wait for a specific value
        >>> ...
        >>> await a.wait_transition()  # wait for a transition (default: any)

    When using `wait_value()` and `wait_transition()`, note that the value may
    have changed again before the caller receives control.
    """

    def __init__(self, value=False):
        if not isinstance(value, _BOOL_TYPES):
            raise TypeError
        self._value = value
        self._level_events = defaultdict(WaitQueue)
        self._edge_events = defaultdict(WaitQueue)

    def __repr__(self):
        return f"AsyncBool(value={self._value})"

    @property
    def value(self):
        """The wrapped value"""
        return self._value

    @value.setter
    def value(self, x):
        if not isinstance(x, _BOOL_TYPES):
            raise TypeError
        if self._value != x:
            self._value = x
            self._level_events[x].unpark_all()
            self._edge_events[x].unpark_all()
            self._edge_events[None].unpark_all()

    async def wait_value(self, value, *, held_for=0):
        """Wait until given value.

        If held_for > 0, the value must match for that duration from the
        time of the call.  "held" means that the value is continuously in the
        requested state.
        """
        if not isinstance(value, _BOOL_TYPES):
            raise TypeError
        while True:
            if value != self.value:
                await self._level_events[value].park()
            else:
                await trio.sleep(0)
            if held_for > 0:
                with trio.move_on_after(held_for):
                    if value == self.value:
                        await self._level_events[not value].park()
                    continue
            break

    # TODO: held_for
    async def wait_transition(self, value=None):
        """Wait until transition to given value (default None which means any)."""
        if not isinstance(value, _BOOL_OR_NONE_TYPES):
            raise TypeError
        await self._edge_events[value].park()

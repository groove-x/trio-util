from ._async_value import AsyncValue


class AsyncBool(AsyncValue):
    """Boolean wrapper offering the ability to wait for a value or transition.

    Synopsis::

        >>> a = AsyncBool()
        >>> ...
        >>> a.value = True   # access underlying value
        >>> ...
        >>> await a.wait_value(False)  # wait for a specific value
        >>> ...
        >>> await a.wait_transition()  # wait for a transition (default: any)

    When using `wait_value()` and `wait_transition()`, note that the value may
    have changed again before the caller receives control.

    Other than the constructor value defaulting to False, this class is the
    same as AsyncValue.
    """

    def __init__(self, value=False):
        super().__init__(value)

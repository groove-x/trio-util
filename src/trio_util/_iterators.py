from collections.abc import AsyncIterator

import trio


class iter_move_on_after(AsyncIterator):
    """async iterator adapter that stops if an iteration exceeds timeout

    The timeout is a duration in seconds.

    Synopsis::

        async for v in iter_move_on_after(5, async_value.eventual_values()):
            ...
    """

    __slots__ = ['_ait', '_timeout']

    def __init__(self, timeout, ait):
        self._ait = ait
        self._timeout = timeout

    async def __anext__(self):
        with trio.move_on_after(self._timeout):
            x = await self._ait.__anext__()
            return x
        raise StopAsyncIteration


class iter_fail_after(AsyncIterator):
    """async iterator adapter that raises trio.TooSlowError if an iteration exceeds timeout

    The timeout is a duration in seconds.

    Synopsis::

        async for v in iter_fail_after(5, async_value.eventual_values()):
            ...
    """

    __slots__ = ['_ait', '_timeout']

    def __init__(self, timeout, ait):
        self._ait = ait
        self._timeout = timeout

    async def __anext__(self):
        with trio.fail_after(self._timeout):
            return await self._ait.__anext__()

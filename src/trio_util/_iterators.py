from typing import AsyncIterator, Generic, TypeVar

import trio


T_co = TypeVar("T_co", covariant=True)


class iter_move_on_after(AsyncIterator[T_co], Generic[T_co]):
    """async iterator adapter that stops if an iteration exceeds timeout

    The timeout is a duration in seconds.

    Synopsis::

        async for v in iter_move_on_after(5, async_value.eventual_values()):
            ...
    """

    __slots__ = ['_ait', '_timeout']

    def __init__(self, timeout: float, ait: AsyncIterator[T_co]) -> None:
        self._ait = ait
        self._timeout = timeout

    async def __anext__(self) -> T_co:
        with trio.move_on_after(self._timeout):
            x = await self._ait.__anext__()
            return x
        raise StopAsyncIteration


class iter_fail_after(AsyncIterator[T_co], Generic[T_co]):
    """async iterator adapter that raises trio.TooSlowError if an iteration exceeds timeout

    The timeout is a duration in seconds.

    Synopsis::

        async for v in iter_fail_after(5, async_value.eventual_values()):
            ...
    """

    __slots__ = ['_ait', '_timeout']

    def __init__(self, timeout: float, ait: AsyncIterator[T_co]) -> None:
        self._ait = ait
        self._timeout = timeout

    async def __anext__(self) -> T_co:
        with trio.fail_after(self._timeout):
            return await self._ait.__anext__()

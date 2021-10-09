from contextlib import asynccontextmanager
from functools import partial
from typing import Awaitable, Callable, AsyncIterator

import trio

from ._awaitables import _wait_and_call


@asynccontextmanager
async def move_on_when(fn: Callable[..., Awaitable],
                       *args, **kwargs) -> AsyncIterator[trio.CancelScope]:
    """Async context manager that exits if async fn(*args, **kwargs) returns.

    The context manager yields a trio.CancelScope.

    Synopsis::

        async with move_on_when(my_event.wait) as cancel_scope:
            cancel_scope.shield = True
            await ...

        # by this point either the body exited, my_event was triggered, or both
    """

    async with trio.open_nursery() as nursery:
        with trio.CancelScope() as cancel_scope:
            nursery.start_soon(_wait_and_call,
                               partial(fn, *args, **kwargs),
                               cancel_scope.cancel)
            yield cancel_scope
        nursery.cancel_scope.cancel()

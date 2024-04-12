from contextlib import asynccontextmanager
from functools import partial
from typing import AsyncGenerator, TYPE_CHECKING

import trio

from ._awaitables import _wait_and_call

if TYPE_CHECKING:  # pragma: no cover
    from typing_extensions import ParamSpec
    from typing import Awaitable, Callable
    Args = ParamSpec("Args")


@asynccontextmanager
async def move_on_when(
    fn: 'Callable[Args, Awaitable[object]]',
    *args: 'Args.args', **kwargs: 'Args.kwargs',
) -> AsyncGenerator[trio.CancelScope, None]:
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


@asynccontextmanager
async def run_and_cancelling(
    fn: 'Callable[Args, Awaitable[object]]',
    *args: 'Args.args', **kwargs: 'Args.kwargs',
) -> AsyncGenerator[None, None]:
    """Async context manager that runs async fn(*args, **kwargs) and cancels it at block exit.

    Synopsis::

        async with run_and_cancelling(my_background_fn, my_arg=10):
            await ...
            # now the block exits, and my_background_fn is cancelled if still running
    """

    async with trio.open_nursery() as nursery:
        nursery.start_soon(partial(fn, *args, **kwargs))
        yield
        nursery.cancel_scope.cancel()

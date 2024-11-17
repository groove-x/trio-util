import functools
from contextlib import asynccontextmanager

import trio
from async_generator import aclosing


def trio_async_generator(wrapped):
    """async generator pattern which supports Trio nurseries and cancel scopes

    Normally, it's not allowed to yield from a Trio nursery or cancel scope when
    implementing async generators.  This decorator makes it possible to do so,
    adapting a generator for safe use.

    Though the wrapped function is written as a normal async generator, usage
    of the wrapper is different:  the wrapper is an async context manager
    providing the async generator to be iterated.

    Synopsis::

        >>> @trio_async_generator
        >>> async def my_generator():
        >>>    # yield values, possibly from a nursery or cancel scope
        >>>    # ...
        >>>
        >>>
        >>> async with my_generator() as agen:
        >>>    async for value in agen:
        >>>        print(value)

    Implementation:  "The idea is that instead of pushing and popping the
    generator from the stack of the task that's consuming it, you instead run
    the generator code as a second task that feeds the consumer task values."
    See https://github.com/python-trio/trio/issues/638#issuecomment-431954073

    ISSUE: pylint is confused by this implementation, and every use will
      trigger not-async-context-manager
    """
    @asynccontextmanager
    @functools.wraps(wrapped)
    async def wrapper(*args, **kwargs):
        send_channel, receive_channel = trio.open_memory_channel(0)  # type: ignore[var-annotated]
        async with trio.open_nursery() as nursery:
            async def adapter():
                async with send_channel, aclosing(wrapped(*args, **kwargs)) as agen:
                    while True:
                        try:
                            # Advance underlying async generator to next yield
                            value = await agen.__anext__()
                        except StopAsyncIteration:
                            break
                        while True:
                            try:
                                # Forward the yielded value into the send channel
                                try:
                                    await send_channel.send(value)
                                except trio.BrokenResourceError:
                                    return
                                break
                            except BaseException as e:  # pylint: disable=broad-except
                                # If send_channel.send() raised (e.g. Cancelled),
                                # throw the raised exception back into the generator,
                                # and get the next yielded value to forward.
                                try:
                                    value = await agen.athrow(e)
                                except StopAsyncIteration:
                                    return

            nursery.start_soon(adapter, name=wrapped)
            async with receive_channel:
                yield receive_channel
    return wrapper

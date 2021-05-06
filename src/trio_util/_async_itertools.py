import anyio


async def _azip(*aiterables, fillvalue, stop_any):
    iters = [item.__aiter__() for item in aiterables]
    while True:
        stop_count = 0
        items = [fillvalue] * len(iters)

        async def collect(i, iterator):
            try:
                items[i] = await iterator.__anext__()
            except StopAsyncIteration:
                nonlocal stop_count
                stop_count += 1  # pylint: disable=undefined-variable

        async with anyio.create_task_group() as nursery:
            for i, iterator in enumerate(iters):
                nursery.start_soon(collect, i, iterator)

        if stop_count >= (1 if stop_any else len(iters)):
            break
        yield tuple(items)


def azip(*aiterables):
    """async version of izip with parallel iteration"""
    return _azip(*aiterables, fillvalue=None, stop_any=True)


def azip_longest(*aiterables, fillvalue=None):
    """async version of izip_longest with parallel iteration"""
    return _azip(*aiterables, fillvalue=fillvalue, stop_any=False)

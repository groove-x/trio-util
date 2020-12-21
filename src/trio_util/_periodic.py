import trio

async def periodic(period):
    """Yield `(elapsed_time, delta_time)` with an interval of `period` seconds.

    For example, to loop indefinitely with a period of 1 second, accounting
    for the time taken in the loop itself::

        async for _ in periodic(1):
            ...

    In the case of overrun, the next iteration begins immediately.

    On the first iteration, `delta_time` will be `None`.
    """
    t0 = trio.current_time()
    t_last, t_start = None, t0
    while True:
        yield t_start - t0, t_start - t_last if t_last is not None else None
        await trio.sleep_until(t_start + period)
        t_last, t_start = t_start, trio.current_time()

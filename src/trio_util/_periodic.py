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
    t_last = None
    while True:
        t_start = t0 if t_last is None else trio.current_time()
        yield t_start - t0, None if t_last is None else t_start - t_last
        user_elapsed = trio.current_time() - t_start
        await trio.sleep(max(0, period - user_elapsed))
        t_last = t_start

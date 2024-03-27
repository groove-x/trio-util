from typing import AsyncGenerator, Optional, Tuple

import trio


async def periodic(period: float) -> AsyncGenerator[Tuple[float, Optional[float]], None]:
    """Yield `(elapsed_time, delta_time)` with an interval of `period` seconds.

    For example, to loop indefinitely with a period of 1 second, accounting
    for the time taken in the loop itself::

        async for _ in periodic(1):
            ...

    In the case of overrun, the next iteration begins immediately.

    On the first iteration, `delta_time` will be `None`.
    """
    t_start = t0 = trio.current_time()
    t_last: Optional[float] = None
    while True:
        if t_last is not None:
            yield t_start - t0, t_start - t_last
        else:
            yield t_start - t0, None
        await trio.sleep_until(t_start + period)
        t_last, t_start = t_start, trio.current_time()

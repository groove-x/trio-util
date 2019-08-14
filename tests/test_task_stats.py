import time

import pytest
import trio

from trio_util import TaskStats


@pytest.mark.parametrize("time_func", [None, time.process_time])
def test_trio_timer(time_func, autojump_clock):
    async def run():
        await trio.sleep(1)
        async with trio.open_nursery() as nursery:
            nursery.start_soon(trio.sleep, 1)
            nursery.start_soon(trio.sleep, 1)

    trio.run(run, clock=autojump_clock, instruments=[TaskStats(time_func)])

import logging

import trio

from trio_util import TaskStats


def test_trio_timer(caplog, autojump_clock):
    caplog.set_level(logging.INFO)

    async def run():
        async with trio.open_nursery() as nursery:
            @nursery.start_soon
            async def _slow_step_task():
                for i in range(3):
                    # simulate a long step time
                    autojump_clock.jump((i + 1) * .1)
                    await trio.sleep(0)

            @nursery.start_soon
            async def _high_reschedule_rate_task():
                for _ in range(100):
                    await trio.sleep(1/100)

    trio.run(run, clock=autojump_clock, instruments=[TaskStats(slow_task_threshold=.015)])
    assert 'slow task step events (> 15 ms)' in caplog.text
    assert '_slow_step_task: 300ms, 200ms' in caplog.text
    assert 'max task schedule rate: 100 Hz' in caplog.text
    assert '_high_reschedule_rate_task' in caplog.text

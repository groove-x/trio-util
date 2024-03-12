from typing import TYPE_CHECKING
import logging

import trio.testing

from trio_util import TaskStats

if TYPE_CHECKING:  # pragma: no cover
    import pytest


def test_task_stats(
    caplog: 'pytest.LogCaptureFixture',
    autojump_clock: trio.testing.MockClock,
) -> None:
    caplog.set_level(logging.INFO)

    async def run() -> None:
        async with trio.open_nursery() as nursery:
            @nursery.start_soon
            async def _slow_step_task() -> None:
                for i in range(3):
                    # simulate a long step time
                    autojump_clock.jump((i + 1) * .1)
                    await trio.sleep(0)

            @nursery.start_soon
            async def _high_reschedule_rate_task() -> None:
                for _ in range(60):
                    await trio.sleep(1/60)

    trio.run(run, clock=autojump_clock, instruments=[TaskStats(slow_task_threshold=.015,
                                                               high_rate_task_threshold=50)])
    assert 'slow task step events (> 15 ms)' in caplog.text
    assert '_slow_step_task: 300ms, 200ms' in caplog.text
    assert 'high task schedule rates' in caplog.text
    assert '_high_reschedule_rate_task' in caplog.text

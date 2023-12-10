import logging
from collections import defaultdict
from typing import Callable, DefaultDict, Dict, List, Optional

import trio

logger = logging.getLogger(__name__)

RATE_MEASURE_PERIOD = .25


class TaskStats(trio.abc.Instrument):
    """Trio scheduler Instrument which logs various task stats at termination.

    Includes max task wait time, slow task steps, and highest task schedule
    rate.
    """
    # TODO: auto thresholds (e.g. > 98th percentile)
    def __init__(
        self, *,
        slow_task_threshold: float = 0.01,
        high_rate_task_threshold: float = 100.0,
        current_time: Callable[[], float] = trio.current_time,
    ) -> None:
        """
        :param slow_task_threshold: tasks with steps higher than this duration
            (seconds) are reported
        :param high_rate_task_threshold: tasks scheduling higher than this rate
            are reported
        :param current_time: function used to retrieve the current time
        """
        super().__init__()
        self.slow_task_threshold = slow_task_threshold
        self.high_rate_task_threshold = high_rate_task_threshold
        self.current_time = current_time
        self.scheduled_start: Dict[trio.lowlevel.Task, float] = {}  # task: start_time
        self.max_wait = 0.0
        self.task_step_start: Optional[float] = None
        self.slow_task_steps: DefaultDict[str, List[float]] = defaultdict(list)  # name: dt_list
        self.schedule_counts: DefaultDict[str, int] = defaultdict(int)  # name: count
        self.rate_start = 0.0
        self.high_schedule_rates: DefaultDict[str, float] = defaultdict(float)  # name: max_rate

    def task_scheduled(self, task: trio.lowlevel.Task) -> None:
        t = self.current_time()
        self.scheduled_start[task] = t
        if t - self.rate_start > RATE_MEASURE_PERIOD:
            for name, count in self.schedule_counts.items():
                rate = count / RATE_MEASURE_PERIOD
                if rate >= self.high_rate_task_threshold:
                    self.high_schedule_rates[name] = max(self.high_schedule_rates[name], rate)
            self.rate_start = t
            self.schedule_counts.clear()
        self.schedule_counts[task.name] += 1

    def before_task_step(self, task: trio.lowlevel.Task) -> None:
        t = self.current_time()
        start = self.scheduled_start.pop(task, None)
        if start:
            dt = t - start
            self.max_wait = max(self.max_wait, dt)
            self.task_step_start = t

    def after_task_step(self, task: trio.lowlevel.Task) -> None:
        start = self.task_step_start
        if start:
            dt = self.current_time() - start
            if dt > self.slow_task_threshold:
                self.slow_task_steps[task.name].append(dt)
            self.task_step_start = None

    def after_run(self) -> None:
        logger.info(f'max task wait time: {self.max_wait * 1000:.2f} ms')
        if self.slow_task_steps:
            text = [f'slow task step events (> {self.slow_task_threshold * 1000:.0f} ms):']
            for name, dt_list in sorted(self.slow_task_steps.items(),
                                        key=lambda item: max(item[1]), reverse=True):
                dt_text = ', '.join(f'{dt * 1000:.0f}ms'
                                    for dt in sorted(dt_list, reverse=True))
                text.append(f'  {name}: {dt_text}')
            logger.info('\n'.join(text))
        if self.high_schedule_rates:
            text = ['high task schedule rates:']
            for name, rate in sorted(self.high_schedule_rates.items(),
                                     key=lambda item: item[1], reverse=True):
                text.append(f'  {name}: {rate:.0f} Hz')
            logger.info('\n'.join(text))

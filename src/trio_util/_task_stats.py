import logging
from collections import defaultdict

import trio

logger = logging.getLogger(__name__)

RATE_MEASURE_PERIOD = .25


class TaskStats(trio.abc.Instrument):
    """Trio scheduler Instrument which logs various task stats at termination.

    Includes max task wait time, slowest task step, and highest task schedule
    rate.
    """
    def __init__(self, current_time=trio.current_time):
        super().__init__()
        self.current_time = current_time
        self.scheduled_start = {}
        self.max_wait = 0
        self.task_step_start = None
        self.max_task_step = (None, 0)
        self.schedule_counts = defaultdict(int)
        self.rate_start = 0
        self.max_schedule_rate = (None, 0)

    def task_scheduled(self, task):
        t = self.current_time()
        self.scheduled_start[task] = t
        if t - self.rate_start > RATE_MEASURE_PERIOD:
            name, count = max(self.schedule_counts.items(),
                              default=(None, 0),
                              key=lambda item: item[1])
            rate = count / RATE_MEASURE_PERIOD
            if rate > self.max_schedule_rate[1]:
                self.max_schedule_rate = (name, rate)
            self.rate_start = t
            self.schedule_counts.clear()
        self.schedule_counts[task.name] += 1

    def before_task_step(self, task):
        t = self.current_time()
        start = self.scheduled_start.pop(task, None)
        if start:
            dt = t - start
            self.max_wait = max(self.max_wait, dt)
            self.task_step_start = t

    def after_task_step(self, task):
        start = self.task_step_start
        if start:
            dt = self.current_time() - start
            if dt > self.max_task_step[1]:
                self.max_task_step = (task.name, dt)
            self.task_step_start = None

    def after_run(self):
        logger.info(f'max task wait time: {self.max_wait * 1000:.2f} ms')
        max_task_name, max_task_time = self.max_task_step
        logger.info(f'slowest task step: {max_task_time * 1000:.2f} ms by {max_task_name}')
        max_rate_name, max_rate = self.max_schedule_rate
        logger.info(f'max task schedule rate: {max_rate:.0f} Hz by {max_rate_name}')

from ._version import __version__
from ._async_bool import AsyncBool
from ._async_itertools import azip, azip_longest
from ._async_value import AsyncValue
from ._awaitables import wait_all, wait_any
from ._cancel_scopes import move_on_when, run_and_cancelling
from ._compose_values import compose_values
from ._exceptions import defer_to_cancelled, multi_error_defer_to
from ._iterators import iter_fail_after, iter_move_on_after
from ._periodic import periodic
from ._repeated_event import RepeatedEvent
from ._task_stats import TaskStats
from ._trio_async_generator import trio_async_generator

def _metadata_fix():
    # don't do this for Sphinx case because it breaks "bysource" member ordering
    import sys
    if 'sphinx' in sys.modules:  # pragma: no cover
        return

    for name, value in globals().items():
        if not name.startswith('_'):
            value.__module__ = __name__

_metadata_fix()

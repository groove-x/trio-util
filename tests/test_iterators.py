import pytest
import trio

from trio_util import iter_move_on_after, iter_fail_after


async def _generator(*durations):
    for i, duration in enumerate(durations):
        await trio.sleep(duration)
        yield i


async def test_iter_move_on_after(autojump_clock):
    last_i = None
    async for i in iter_move_on_after(20, _generator(0, 1, 1, 5, 1)):
        last_i = i
    assert last_i == 4


async def test_iter_move_on_after_caught(autojump_clock):
    last_i = None
    async for i in iter_move_on_after(2, _generator(0, 1, 1, 5, 1)):
        last_i = i
    assert last_i == 2


async def test_iter_fail_after(autojump_clock):
    last_i = None
    async for i in iter_fail_after(20, _generator(0, 1, 1, 5, 1)):
        last_i = i
    assert last_i == 4


async def test_iter_fail_after_caught(autojump_clock):
    with pytest.raises(trio.TooSlowError):
        last_i = None
        try:
            async for i in iter_fail_after(2, _generator(0, 1, 1, 5, 1)):
                last_i = i
        finally:
            assert last_i == 2

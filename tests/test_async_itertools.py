from itertools import zip_longest

import trio

from trio_util import azip, azip_longest


async def periodic_iter(it):
    for x in it:
        yield x
        await trio.sleep(1)


async def test_azip(autojump_clock):
    t0 = trio.current_time()
    expected = zip(range(5), range(3), range(3))
    async for item in azip(
            periodic_iter(range(5)), periodic_iter(range(3)), periodic_iter(range(3))):
        assert item == next(expected)
    assert trio.current_time() - t0 == 3


async def test_azip_longest(autojump_clock):
    t0 = trio.current_time()
    expected = zip_longest(range(5), range(3), fillvalue=-10)
    async for item in azip_longest(
            periodic_iter(range(5)), periodic_iter(range(3)), fillvalue=-10):
        assert item == next(expected)
    assert trio.current_time() - t0 == 5

import trio

from trio_util import periodic

async def test_periodic(autojump_clock):
    count = 0
    t0 = trio.current_time()
    async for elapsed, dt in periodic(1.5):
        assert elapsed == count * 1.5
        assert dt == (1.5 if count != 0 else None)
        if count == 3:
            break
        await trio.sleep(.123)
        count += 1
    total_elapsed = trio.current_time() - t0
    assert total_elapsed == 4.5

async def test_periodic_overrun(autojump_clock):
    count = 0
    t0 = trio.current_time()
    async for elapsed, dt in periodic(1.5):
        assert elapsed == count * 5
        assert dt == (5 if count != 0 else None)
        if count == 3:
            break
        await trio.sleep(5)
        count += 1
    total_elapsed = trio.current_time() - t0
    # Each iteration had an overrun, so duration passed to
    # periodic is effectively ignored.
    assert total_elapsed == 15

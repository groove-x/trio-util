from functools import partial

import trio

from trio_util import wait_all, wait_any


async def test_all(nursery: trio.Nursery, autojump_clock: trio.abc.Clock) -> None:
    count = 0

    async def foo(duration: int) -> None:
        await trio.sleep(duration)
        nonlocal count
        count += 1

    await wait_all(partial(foo, 1), partial(foo, 2))
    assert count == 2


async def test_any(nursery: trio.Nursery, autojump_clock: trio.abc.Clock) -> None:
    count = 0

    async def foo(duration: int) -> None:
        await trio.sleep(duration)
        nonlocal count
        count += 1

    await wait_any(partial(foo, 1), partial(foo, 2))
    assert count == 1

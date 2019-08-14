import trio


async def _wait_and_call(f1, f2):
    """await on f1() and call f2()"""
    await f1()
    f2()


async def wait_any(*args):
    """Wait until any of the given async functions are completed.

    Equivalent to creating a new nursery and calling `start_soon()` on
    each async function, where the first function to return will cause the
    nursery to be cancelled.

    If the function invocations require arguments, use partial()::

        await wait_any(partial(foo, 'hello'),
                       partial(bar, debug=True))
    """
    async with trio.open_nursery() as nursery:
        cancel = nursery.cancel_scope.cancel
        for f in args:
            nursery.start_soon(_wait_and_call, f, cancel)


async def wait_all(*args):
    """Wait until all of the given async functions are completed.

    Equivalent to creating a new nursery and calling `start_soon()` on
    each async function.

    NOTE: Be careful when using this with a function that returns when
    some non-permanent condition is satisfied (e.g. `AsyncBool.wait_value`).
    While waiting for the other async function to complete, the state which
    satisfied the condition may change.
    """
    async with trio.open_nursery() as nursery:
        for f in args:
            nursery.start_soon(f)

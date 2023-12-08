from typing import Any, AsyncIterable, AsyncIterator, Tuple, TypeVar, Union, overload

import trio


T = TypeVar("T")
T1 = TypeVar("T1")
T2 = TypeVar("T2")
T3 = TypeVar("T3")
T4 = TypeVar("T4")
T5 = TypeVar("T5")
FillT = TypeVar("FillT")


async def _azip(aiterables: Tuple[AsyncIterable[Any], ...], fillvalue: object, stop_any: bool) -> AsyncIterator[Tuple[Any, ...]]:
    iters = [item.__aiter__() for item in aiterables]
    while True:
        stop_count = 0
        items: list[object] = [fillvalue] * len(iters)

        async def collect(i: int, iterator: AsyncIterator[object]) -> None:
            try:
                items[i] = await iterator.__anext__()
            except StopAsyncIteration:
                nonlocal stop_count
                stop_count += 1  # pylint: disable=undefined-variable

        async with trio.open_nursery() as nursery:
            for i, iterator in enumerate(iters):
                nursery.start_soon(collect, i, iterator)

        if stop_count >= (1 if stop_any else len(iters)):
            break
        yield tuple(items)


@overload
def azip() -> AsyncIterator[Tuple[()]]: ...
@overload
def azip(__it1: AsyncIterable[T1]) -> AsyncIterator[Tuple[T1]]: ...
@overload
def azip(
    __it1: AsyncIterable[T1], __it2: AsyncIterable[T2],
) -> AsyncIterator[Tuple[T1, T2]]: ...
@overload
def azip(
    __it1: AsyncIterable[T1], __it2: AsyncIterable[T2], __it3: AsyncIterable[T3],
) -> AsyncIterator[Tuple[T1, T2, T3]]: ...
@overload
def azip(
    __it1: AsyncIterable[T1], __it2: AsyncIterable[T2], __it3: AsyncIterable[T3],
    __it4: AsyncIterable[T4]) -> AsyncIterator[Tuple[T1, T2, T3, T4]]: ...
@overload
def azip(
    __it1: AsyncIterable[T1], __it2: AsyncIterable[T2], __it3: AsyncIterable[T3],
    __it4: AsyncIterable[T4], __it5: AsyncIterable[T5],
) -> AsyncIterator[Tuple[T1, T2, T3, T4, T5]]: ...
@overload
def azip(*aiterables: AsyncIterable[Any]) -> AsyncIterator[Tuple[Any, ...]]: ...
def azip(*aiterables: AsyncIterable[Any]) -> AsyncIterator[Any]:
    """async version of zip() with parallel iteration"""
    return _azip(aiterables, fillvalue=None, stop_any=True)


# See typeshed's itertools.pyi for the reasoning behind these overloads.

# One iterable, fillvalue is irrelevant.
@overload
def azip_longest(__it1: AsyncIterable[T1], *, fillvalue: object = ...) -> AsyncIterator[Tuple[T1]]: ...
# Two iterables
@overload
def azip_longest(
    __it1: AsyncIterable[T1], __it2: AsyncIterable[T2],
) -> AsyncIterator[Tuple[Union[T1, Any], Union[T2, Any]]]: ...
@overload
def azip_longest(
    __it1: AsyncIterable[T1], __it2: AsyncIterable[T2],
    *, fillvalue: FillT,
) -> AsyncIterator[Tuple[Union[T1, FillT], Union[T2, FillT]]]: ...
# Three iterables
@overload
def azip_longest(
    __it1: AsyncIterable[T1], __it2: AsyncIterable[T2], __it3: AsyncIterable[T3],
) -> AsyncIterator[Tuple[Union[T1, Any], Union[T2, Any], Union[T3, Any]]]: ...
@overload
def azip_longest(
    __it1: AsyncIterable[T1], __it2: AsyncIterable[T2], __it3: AsyncIterable[T3],
    *, fillvalue: FillT,
) -> AsyncIterator[Tuple[Union[T1, FillT], Union[T2, FillT], Union[T3, FillT]]]: ...
# Four iterables
@overload
def azip_longest(
    __it1: AsyncIterable[T1], __it2: AsyncIterable[T2], __it3: AsyncIterable[T3],
    __it4: AsyncIterable[T4]) -> AsyncIterator[Tuple[T1, T2, T3, T4]]: ...
# Five iterables
@overload
def azip_longest(
    __it1: AsyncIterable[T1], __it2: AsyncIterable[T2], __it3: AsyncIterable[T3],
    __it4: AsyncIterable[T4], __it5: AsyncIterable[T5],
) -> AsyncIterator[Tuple[T1, T2, T3, T4, T5]]: ...
# Six or more
@overload
def azip_longest(
    __it1: AsyncIterable[T], __it2: AsyncIterable[T], __it3: AsyncIterable[T],
    __it4: AsyncIterable[T], __it5: AsyncIterable[T],
    *aiterables: AsyncIterable[T],
) -> AsyncIterator[Tuple[Union[T, Any], ...]]: ...
@overload
def azip_longest(
    __it1: AsyncIterable[T], __it2: AsyncIterable[T], __it3: AsyncIterable[T],
    __it4: AsyncIterable[T], __it5: AsyncIterable[T],
    *aiterables: AsyncIterable[T],
    fillvalue: T,
) -> AsyncIterator[Tuple[T, ...]]: ...
def azip_longest(*aiterables: AsyncIterable[Any], fillvalue: object = None) -> AsyncIterator[Tuple[Any, ...]]:
    """async version of zip_longest() with parallel iteration"""
    return _azip(aiterables, fillvalue=fillvalue, stop_any=False)

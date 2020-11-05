import trio

from ._async_bool import AsyncBool


class UnqueuedRepeatedEvent:
    """An unqueued repeated event that supports broadcast

    The event may be triggered multiple times, and supports multiple listeners.
    A listener will miss an event if it's blocked processing the previous one.

    >>> event = UnqueuedRepeatedEvent()

    A task listens for events:

    >>> async for _ in event:
    >>>    # do blocking work
    >>>    await trio.sleep(1)

    Another task triggers events:

    >>> event.set()    # trigger event
    >>> trio.sleep(0)  # listener will enter loop body
    >>> event.set()    # listener misses this event since it's still in the loop body
    >>> trio.sleep(2)
    >>> event.set()    # listener will enter loop body again
    """

    def __init__(self):
        self._event = AsyncBool()

    def set(self):
        """Trigger event."""
        self._event.value ^= True

    async def __aiter__(self):
        async for _ in self._event.transitions():
            yield


class MailboxRepeatedEvent:
    """A single-listener repeated event with one queue slot

    MailboxRepeatedEvent is used to coordinate some work whenever a collection
    or other stateful object is mutated.  Although you may miss intermediate
    states, you're ensured to eventually receive an event to process the most
    recent state.

    >>> my_list = []
    >>> repeated_event = MailboxRepeatedEvent()

    Whenever your collection is mutated, simply call the `set()` method.

    >>> my_list.append('hello')
    >>> repeated_event.set()

    The listener to continually process the latest state is simply:

    >>> async for _ in repeated_event:
    >>>     await persist_to_storage(my_list)

    Even if you exit the listen loop and start a new one, you'll still receive
    an event if a `set()` occurred in the meantime.  Due to this statefulness,
    only one listener is allowed-- a second listener will encounter a RuntimeError.

    To avoid false positives from the "multiple listener" check, it's advised
    to use `aclosing()` (from the async_generator package or Python 3.10) for
    deterministic cleanup of the generator:

    >>> async with aclosing(repeated_event.__aiter__()) as events:
    >>>     async for _ in events:
    >>>         await persist_to_storage(my_list)
    """

    def __init__(self):
        self._event = trio.Event()
        self._iteration_open = False

    def set(self):
        """Trigger event

        Up to one event may be queued if there is no waiting listener (i.e.
        no listener, or the listener is still processing the previous event).
        """
        self._event.set()

    async def __aiter__(self):
        """NOTE: be sure to use with `aclosing()`"""
        if self._iteration_open:
            raise RuntimeError(f'{self.__class__.__name__} can only have one listener')
        self._iteration_open = True
        try:
            while True:
                await self._event.wait()
                self._event = trio.Event()
                yield
        finally:
            self._iteration_open = False

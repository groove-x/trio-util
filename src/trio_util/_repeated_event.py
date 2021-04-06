from ._async_value import AsyncValue


class RepeatedEvent:
    """A repeated event that supports multiple listeners.

    RepeatedEvent supports both "unqueued" and "eventual consistency" uses:

        * unqueued - drop events while processing the previous one
        * eventual consistency - some events may be missed while processing the
          previous one, but receiving the latest event is ensured
    """

    def __init__(self):
        self._event = AsyncValue(0)

    def set(self):
        """Trigger an event"""
        self._event.value += 1

    async def wait(self):
        """Wait for the next event"""
        token = self._event.value
        await self._event.wait_value(lambda val: val > token)

    async def unqueued_events(self):
        """Unqueued event iterator

        The listener will miss an event if it's blocked processing the previous
        one.  This is effectively the same as the following manual loop::

        >>> while True:
        >>>     await event.wait()
        >>>     # do work...

        Typical usage::

            >>> event = RepeatedEvent()

            A task listens for events:

            >>> async for _ in event.unqueued_events():
            >>>    # do blocking work
            >>>    await trio.sleep(1)

            Another task triggers events:

            >>> event.set()    # trigger event
            >>> trio.sleep(0)  # listener will enter loop body
            >>> event.set()    # listener misses this event since it's still in the loop body
            >>> trio.sleep(2)
            >>> event.set()    # listener will enter loop body again
        """
        async for _ in self._event.transitions():
            yield

    async def events(self, *, repeat_last=False):
        """Event iterator with eventual consistency

        Use this iterator to coordinate some work whenever a collection
        or other stateful object is mutated.  Although you may miss intermediate
        states, you're ensured to eventually receive an event to process the most
        recent state.  (https://en.wikipedia.org/wiki/Eventual_consistency)

        :param repeat_last: if true, repeat the last position in the event
          stream.  If no event has been set yet it still yields immediately,
          representing the "start" position.

        Typical usage::

            >>> my_list = []
            >>> repeated_event = RepeatedEvent()

            Whenever your collection is mutated, call the `set()` method.

            >>> my_list.append('hello')
            >>> repeated_event.set()

            The listener to continually process the latest state is:

            >>> async for _ in repeated_event.events():
            >>>     await persist_to_storage(my_list)

            If you'd like to persist the initial state of the list (before any
            set() is called), use the `repeat_last=True` option.
        """
        token = self._event.value
        if repeat_last:
            token -= 1
        async for _ in self._event.eventual_values(lambda val: val > token):
            yield

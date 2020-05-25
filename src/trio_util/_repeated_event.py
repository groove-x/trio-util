try:
    from trio.lowlevel import ParkingLot as WaitQueue
except ImportError:
    from trio.hazmat import ParkingLot as WaitQueue


class UnqueuedRepeatedEvent:
    """An unqueued repeated event.

    A repeated event may be triggered multiple times, and has only one
    listener.  A call to set() is ignored if the listener is still processing
    the previous event (or there is no listener), and won't be queued.

    >>> event = UnqueuedRepeatedEvent()

    One task runs a listening loop, waiting for set():

    >>> async for _ in event:
    >>>    # do blocking work
    >>>    await trio.sleep(1)

    Another task triggers events:

    >>> event.set()  # trigger event
    >>> trio.sleep(0)  # event processing starts
    >>> event.set()  # ignored, because previous event is still being processed
    >>> trio.sleep(2)
    >>> event.set()  # trigger event
    """

    def __init__(self):
        self._wait_queue = WaitQueue()
        self._iteration_open = False

    def set(self):
        """Trigger event if there is a waiting listener."""
        self._wait_queue.unpark_all()

    def __aiter__(self):
        if self._iteration_open:
            raise RuntimeError(f'{self.__class__.__name__} can only have one listener')
        return self._listen()

    async def _listen(self):
        self._iteration_open = True
        try:
            while True:
                await self._wait_queue.park()
                yield
        finally:
            self._iteration_open = False


class MailboxRepeatedEvent:
    """A repeated event which queues up to one set() call.

    A repeated event may be triggered multiple times, and has only one
    listener.  Up to one set() call may be queued if the listener is
    still processing the previous event.

    It's often used for signaling that an out-of-band data location has
    changed (hence the name "mailbox").  If the data is a collection type
    (list, etc.) it's safe to use this class, but other types of data are
    subject to overrun.

    AVOID USING THIS CLASS FOR NON-COLLECTION DATA because data changes can
    be lost if the listener does not keep up.  Consider using a queue instead
    (see trio.open_memory_channel) so that there is back pressure ensuring
    that the data is received.

    >>> event = MailboxRepeatedEvent()
    >>> data = None

    One task runs a listening loop, waiting for set():

    >>> async for _ in event:
    >>>    # process data
    >>>    print(data)
    >>>    await trio.sleep(1)

    Another task triggers iteration:

    >>> data = 'foo'
    >>> event.set()  # trigger event
    >>> trio.sleep(0)  # event processing starts
    >>> data = 'bar'
    >>> event.set()  # trigger event (queued since previous event is being processed)
    """

    def __init__(self):
        self._requested = False
        self._wait_queue = WaitQueue()
        self._iteration_open = False

    def set(self):
        """Trigger event

        Up to one event may be queued if there is no waiting listener (i.e.
        no listener, or the listener is still processing the previous event).
        """
        self._requested = True
        self._wait_queue.unpark_all()

    def __aiter__(self):
        if self._iteration_open:
            raise RuntimeError(f'{self.__class__.__name__} can only have one listener')
        return self._listen()

    async def _listen(self):
        self._iteration_open = True
        try:
            while True:
                if not self._requested:
                    await self._wait_queue.park()
                self._requested = False
                yield
        finally:
            self._iteration_open = False

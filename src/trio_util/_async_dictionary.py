from typing import TypeVar, MutableMapping

import trio


KT = TypeVar('KT')
VT = TypeVar('VT')


class AsyncDictionary(MutableMapping[KT, VT]):
    """MutableMapping with waitable get and pop.

    TODO: exception support using outcome package
    """

    def __init__(self, *args, **kwargs):
        self._store = dict(*args, **kwargs)
        self._pending = {}  # key: Event

    def __getitem__(self, key):
        return self._store[key]

    async def get_wait(self, key: KT) -> VT:
        """Return value of given key, blocking until populated."""
        if key in self._store:
            return self._store[key]
        if key not in self._pending:
            self._pending[key] = trio.Event()
        await self._pending[key].wait()
        return self._store[key]

    async def pop_wait(self, key: KT) -> VT:
        """Remove key and return its value, blocking until populated."""
        value = await self.get_wait(key)
        del self._store[key]
        return value

    def is_waiting(self, key: KT) -> bool:
        """Return True if there is a task waiting for key."""
        return key in self._pending

    def __setitem__(self, key, value):
        self._store[key] = value
        if key in self._pending:
            self._pending.pop(key).set()

    def __delitem__(self, key):
        del self._store[key]

    def __iter__(self):
        return iter(self._store)

    def __len__(self):
        return len(self._store)

    def __repr__(self):
        return repr(self._store)

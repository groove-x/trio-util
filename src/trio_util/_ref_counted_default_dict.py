from typing import Callable, DefaultDict, Generator, Generic, TypeVar, overload
from collections import defaultdict
from contextlib import contextmanager


K = TypeVar("K")
V = TypeVar("V")


class _RefCountedDefaultDict(DefaultDict[K, V], Generic[K, V]):
    """defaultdict offering deterministic collection of unreferenced keys"""

    # Add in other __init__ overloads if required.
    def __init__(self, default_factory: Callable[[], V]) -> None:
        super().__init__(default_factory)
        self.refs_by_key: DefaultDict[K, int] = defaultdict(int)

    @contextmanager
    def open_ref(self, key: K) -> Generator[V, None, None]:
        """Context manager that holds a reference to key, yielding the corresponding value

        At context exit, the given key will be deleted if there are no other
        open references.
        """
        self.refs_by_key[key] += 1
        try:
            yield self[key]
        finally:
            self.refs_by_key[key] -= 1
            if self.refs_by_key[key] == 0:
                del self[key]
                del self.refs_by_key[key]

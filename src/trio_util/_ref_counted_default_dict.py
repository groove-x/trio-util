from collections import defaultdict
from contextlib import contextmanager


class _RefCountedDefaultDict(defaultdict):
    """defaultdict offering deterministic collection of unreferenced keys"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.refs_by_key = defaultdict(int)

    @contextmanager
    def open_ref(self, key):
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

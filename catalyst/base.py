"""Abstract base class.

This is necessary to avoid circular imports between core.py and fields.py.
"""


class CatalystABC:
    """Abstract base class from which Catalyst inherit."""
    fields = {}

    def dump(self, data, raise_error=None):
        raise NotImplementedError

    def load(self, data, raise_error=None):
        raise NotImplementedError

    def dump_many(self, data, raise_error=None):
        raise NotImplementedError

    def load_many(self, data, raise_error=None):
        raise NotImplementedError

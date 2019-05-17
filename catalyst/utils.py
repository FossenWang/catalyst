from typing import Mapping

from .exceptions import ValidationError


class ErrorMessageMixin:
    default_error_messages = {}
    unknown_error = "Unknown error."

    def collect_error_messages(self, error_messages: dict = None):
        """
        Collect default error message from self and parent classes.

        :param error_messages: message dict, defaults to None
        :type error_messages: dict, optional
        """
        messages = {}
        for cls in reversed(self.__class__.__mro__):
            messages.update(getattr(cls, 'default_error_messages', {}))
        messages.update(error_messages or {})
        self.error_messages = messages

    def error(self, error_key: str, error_class=ValidationError):
        raise error_class(
            self.error_messages.get(error_key, self.unknown_error))


def get_attr_or_item(obj, name):
    if isinstance(obj, Mapping):
        return obj[name]
    return getattr(obj, name)


def get_item(mapping, key):
    return mapping[key]


dump_from_attribute_or_key = get_attr_or_item
dump_from_attribute = getattr
dump_from_key = get_item


class _Missing:
    def __repr__(self):
        return '<catalyst.missing>'

# Default value for field args `dump_default` and `load_default`
# which means that the field does not exist in data.
# KeyError or AttributeError will be raised if dumping field is missing.
# Field will be excluded from load result if loading field is missing.
missing = _Missing()

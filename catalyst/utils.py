from typing import Mapping

from .exceptions import ValidationError


class ErrorMessageMixin:
    default_error_messages = {}

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

    def error(self, error_key: str):
        raise ValidationError(self.error_messages.get(error_key))


def get_attr_or_item(obj, name):
    if hasattr(obj, name):
        return getattr(obj, name)

    if isinstance(obj, Mapping) and name in obj:
        return obj.get(name)

    raise AttributeError(f'{obj} has no attribute or key "{name}".')


def get_item(mapping, key):
    return mapping[key]


dump_from_attribute_or_key = get_attr_or_item
dump_from_attribute = getattr
dump_from_key = get_item

from typing import Mapping, Callable
from types import MappingProxyType

from .exceptions import ValidationError


class LoadResultMixin:
    def __repr__(self):
        if not self.is_valid:
            return 'LoadResult(is_valid=%s, errors=%s)' % (self.is_valid, self.format_errors())
        return 'LoadResult(is_valid=%s, valid_data=%s)' % (self.is_valid, super().__repr__())

    def __str__(self):
        if not self.is_valid:
            return str(self.format_errors())
        return super().__repr__()

    def format_errors(self):
        return {k: str(self.errors[k]) for k in self.errors}

    @property
    def is_valid(self):
        return not self.errors


class LoadDict(LoadResultMixin, dict):
    def __init__(self, valid_data: dict = None, errors: dict = None, invalid_data: dict = None):
        super().__init__(valid_data if valid_data else {})
        self.valid_data = MappingProxyType(self)
        self.errors = errors if errors else {}
        self.invalid_data = invalid_data if invalid_data else {}

    def update(self, E, **F):
        if isinstance(E, self.__class__):
            self.invalid_data.update(E.invalid_data)
            self.errors.update(E.errors)
        super().update(E, **F)


class LoadList(LoadResultMixin, list):
    pass



class ErrorMessageMixin:
    default_error_class = ValidationError
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

    def error(self, error_key: str, error_class=None):
        if not error_class:
            error_class = self.default_error_class
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


def no_processing(value):
    return value


def snake_to_camel(snake: str) -> str:
    camel = snake.title().replace('_', '')
    if camel:
        camel = camel[0].lower() + camel[1:]
    return camel


def ensure_staticmethod(func: Callable) -> staticmethod:
    if isinstance(func, staticmethod):
        return func
    return staticmethod(func)

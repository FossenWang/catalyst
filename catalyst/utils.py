from typing import Mapping, Callable, Iterable

from .exceptions import ValidationError


class Result:
    def __init__(self, valid_data: Iterable, errors: Mapping, invalid_data: Mapping):
        self.valid_data = valid_data
        self.errors = errors
        self.invalid_data = invalid_data

    def __repr__(self):
        return (
            f'{self.__class__.__name__}('
            f'valid_data={self.valid_data}, '
            f'errors={self.errors}, '
            f'invalid_data={self.invalid_data})'
        )

    def __str__(self):
        if self.is_valid:
            return str(self.valid_data)
        return str(self.format_errors())

    @classmethod
    def _format_errors(cls, errors: Mapping):
        if isinstance(errors, Mapping):
            return {k: cls._format_errors(errors[k]) for k in errors}
        return str(errors)

    def format_errors(self):
        return self._format_errors(self.errors)

    @property
    def is_valid(self):
        return not self.errors


class DumpResult(Result):
    pass


class LoadResult(Result):
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


class OptionBox:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if value is not None:
                setattr(self, key, value)

    def get(self, **kwargs):
        if len(kwargs) != 1:
            raise ValueError('Only accept one pairs of kwargs.')
        for key, value in kwargs.items():
            if value is None:
                return getattr(self, key)
            return value


class _Missing:
    def __repr__(self):
        return '<catalyst.missing>'

# Default value for field args `dump_default` and `load_default`
# which means that the field does not exist in data.
# KeyError or AttributeError will be raised if dumping field is missing.
# Field will be excluded from load result if loading field is missing.
missing = _Missing()


def get_attr_or_item(obj, name, default):
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def get_item(mapping, key, default):
    # return mapping.get(key, default)
    if isinstance(mapping, Mapping):
        return mapping.get(key, default)
    raise TypeError(f'{mapping} is not Mapping.')


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

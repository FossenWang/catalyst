from typing import Mapping, Iterable

from .exceptions import ValidationError


class CatalystResult:
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
    def _format_errors(cls, errors):
        if isinstance(errors, Mapping):
            return {k: cls._format_errors(errors[k]) for k in errors}
        return str(errors)

    def format_errors(self):
        return self._format_errors(self.errors)

    @property
    def is_valid(self):
        return not self.errors


class DumpResult(CatalystResult):
    pass


class LoadResult(CatalystResult):
    pass


# global error messages, {'class': {'error_key': 'error_message'}}
ERROR_MESSAGES = {}
UNKNOWN_ERROR_MESSAGE = (
    'Error key `{key}` does not exist in the `error_messages` dict of `{self}`.'
)

class ErrorMessageMixin:
    def collect_error_messages(self, error_messages: dict = None):
        """
        Collect default error message from self and parent classes.

        :param error_messages: message dict, defaults to None
        :type error_messages: dict, optional
        """
        messages = {}
        for cls in reversed(self.__class__.__mro__):
            messages.update(ERROR_MESSAGES.get(cls, {}))
        messages.update(error_messages or {})
        self.error_messages = messages

    def error(self, error_key: str, **kwargs):
        raise self.get_error(error_key, **kwargs)

    def get_error(self, error_key: str, **kwargs):
        try:
            msg = self.error_messages[error_key]
        except KeyError:
            raise AssertionError(UNKNOWN_ERROR_MESSAGE.format(self=self, key=error_key))

        msg = str(msg).format(self=self, **kwargs)
        return ValidationError(msg)


class OptionBox:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if value is not None:
                setattr(self, key, value)

    def get(self, **kwargs):
        if len(kwargs) != 1:
            raise ValueError('Only accept a pair of kwargs.')
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


def assign_attr_or_item_getter(obj):
    if isinstance(obj, Mapping):
        return Mapping.get
    return getattr


def assign_item_getter(obj):
    if isinstance(obj, Mapping):
        return Mapping.get
    raise TypeError(f'{obj} is not Mapping.')


def no_processing(value):
    return value


def snake_to_camel(snake: str) -> str:
    camel = snake.title().replace('_', '')
    if camel:
        camel = camel[0].lower() + camel[1:]
    return camel

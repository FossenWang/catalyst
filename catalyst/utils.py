from typing import Mapping, Iterable, Dict

from .exceptions import ValidationError


class BaseResult:
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


class DumpResult(BaseResult):
    pass


class LoadResult(BaseResult):
    pass


UNKNOWN_ERROR_MESSAGE = (
    'Exception raised by "{self}", but error key "{key}" '
    'does not exist in the "error_messages" dict.'
)

class ErrorMessageMixin:
    """A helper mixin for error messages management.
    Class attribute `cls.error_messages` stores default error messages.
    Error messages will be collect into `self.error_messages` in the order
    of class inheritance, and can be overrided by `error_messages` argument.
    """
    error_cls = ValidationError
    error_messages: Dict[str, str] = {}

    def collect_error_messages(self, error_messages: Dict[str, str] = None):
        """Collect default error messages from self and parent classes.

        :param error_messages: Its keys are used to find message, values are
            string which support format syntax, and always takes an argument
            named `self` which is the instance.
        """
        messages = {}
        for cls in reversed(self.__class__.__mro__):
            messages.update(cls.__dict__.get('error_messages', {}))
        messages.update(error_messages or {})
        self.error_messages: Dict[str, str] = messages

    def get_error_message(self, error_key: str, **kwargs):
        """Get formated error message according to `error_key`.
        Can be interpolated with `self` and other `kwargs`.

        :param error_key: Key of `self.error_messages`.
        :param kwargs: Passed to `str.format` method.
        """
        try:
            msg = self.error_messages[error_key]
        except KeyError as error:
            msg = UNKNOWN_ERROR_MESSAGE.format(self=self, key=error_key)
            raise AssertionError(msg) from error
        return msg.format(self=self, **kwargs)

    def error(self, error_key: str, **kwargs):
        """Return exception with message according to `error_key`."""
        return self.error_cls(self.get_error_message(error_key, **kwargs))


def bind_attrs(obj, **kwargs):
    """Set not None attrbutes."""
    for key, value in kwargs.items():
        if value is not None:
            setattr(obj, key, value)


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
    raise TypeError(f'"{obj}" is not Mapping.')


def no_processing(value):
    return value


def snake_to_camel(snake: str) -> str:
    camel = snake.title().replace('_', '')
    if camel:
        camel = camel[0].lower() + camel[1:]
    return camel


def copy_keys(mapping: Mapping, keys: Iterable) -> dict:
    """Copy values from mapping by keys."""
    return {key: mapping[key] for key in keys if key in mapping}

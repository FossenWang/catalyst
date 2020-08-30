from typing import Iterable, Mapping, Hashable, Callable as CallableType

from ..utils import copy_keys, bind_attrs
from ..validators import LengthValidator, RegexValidator

from .base import Field


class ConstantField(Field):
    """Constant Field."""

    def __init__(self, constant, **kwargs):
        super().__init__(**kwargs)
        self.constant = constant
        self.dump_default = constant
        self.load_default = constant

    def dump(self, value):
        return self.constant

    def load(self, value):
        return self.constant


class StringField(Field):
    """String Field.

    :param min_length: The minimum length of the value.
    :param max_length: The maximum length of the value.
    :param regex: The regular expression that the value must match.
    :param error_messages: Keys {'too_small', 'too_large', 'not_between', 'no_match', ...}.
    """
    parse = format = str

    def __init__(
            self,
            min_length: int = None,
            max_length: int = None,
            regex: str = None,
            **kwargs):
        super().__init__(**kwargs)
        self.min_length = min_length
        self.max_length = max_length
        self.regex = regex

        if min_length is not None or max_length is not None:
            msg_dict = copy_keys(self.error_messages, ('too_small', 'too_large', 'not_between'))
            self.add_validator(LengthValidator(min_length, max_length, msg_dict))
        if regex:
            msg = self.error_messages.get('no_match')
            self.add_validator(RegexValidator(regex, msg))


class BooleanField(Field):
    """Boolean field.

    :param value_map: Values that will be onverted to `True` or `False`.
        The keys are `True` and `False`, values are `Hashable`.
    """
    value_map = {
        True: ('1', 'y', 'yes', 'true', 'True'),
        False: ('0', 'n', 'no', 'false', 'False'),
    }

    def __init__(self, value_map: dict = None, **kwargs):
        super().__init__(**kwargs)
        bind_attrs(self, value_map=value_map)
        self.reverse_value_map = {
            raw: parsed
            for parsed, raw_values in self.value_map.items()
            for raw in raw_values}

    def format(self, value):
        if isinstance(value, Hashable):
            value = self.reverse_value_map.get(value, value)
        return bool(value)

    parse = format


class CallableField(Field):
    """Field to dump the result of a callable, such as object method.
    This field dose not participate in the loading process by default.

    :param func_args: Arguments passed to callable.
    :param func_kwargs: Keyword arguments passed to callable.
    """
    no_load = True
    func_args = tuple()
    func_kwargs = {}

    def __init__(self, func_args: Iterable = None, func_kwargs: Mapping = None, **kwargs):
        super().__init__(**kwargs)
        if func_args is None:
            func_args = self.func_args
        if func_kwargs is None:
            func_kwargs = self.func_kwargs
        # set and check params
        self.set_args(*func_args, **func_kwargs)

    def set_args(self, *args, **kwargs):
        self.func_args = args
        self.func_kwargs = kwargs

    def format(self, func: CallableType):
        return func(*self.func_args, **self.func_kwargs)

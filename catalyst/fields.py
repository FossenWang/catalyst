"Fields"

from typing import Callable, Dict, Any, NoReturn, List
from collections import Iterable
from datetime import datetime, time, date

from .validators import (
    ValidationError, LengthValidator, ComparisonValidator,
    BoolValidator
)


def no_processing(value): return value


Name = str
Value = Any


class Field:
    default_error_messages = {
        'required': 'Missing data for required field.',
        'allow_none': 'Field may not be None.'
    }

    def __init__(
        self,
        name: str = None,
        key: str = None,
        dump_from: Callable[[object, Name], Value] = None,
        formatter: Callable[[Value], Value] = None,
        parse: Callable[[Value], Value] = None,
        validators: Callable[[Value], None] = None,
        required: bool = False,
        allow_none: bool = True,
        error_messages: Dict[str, str] = None,
        no_dump: bool = False,
        no_load: bool = False,
    ):
        self.name = name
        self.key = key
        self.required = required
        self.allow_none = allow_none
        self.no_dump = no_dump
        self.no_load = no_load

        self.dump_from = dump_from if dump_from else getattr

        self.formatter = formatter if formatter else no_processing

        self.parse = parse if parse else no_processing

        self.set_validators(validators)

        # Collect default error message from self and parent classes
        messages = {}
        for cls in reversed(self.__class__.__mro__):
            messages.update(getattr(cls, 'default_error_messages', {}))
        messages.update(error_messages or {})
        self.error_messages = messages

    def set_dump_from(self, dump_from: Callable[[object, Name], Value]):
        self.dump_from = dump_from
        return dump_from

    def set_formatter(self, formatter: Callable[[Value], Value]):
        self.formatter = formatter
        return formatter

    def set_parse(self, parse: Callable[[Value], Value]):
        self.parse = parse
        return parse

    def set_validators(self, validators: List[Callable[[Value], None]]):
        if isinstance(validators, Iterable):
            self.validators = validators
        elif validators:
            self.validators = [validators]
        else:
            self.validators = []
        return validators

    def add_validator(self, validator: Callable[[Value], None]):
        self.validators.append(validator)
        return validator

    def dump(self, obj):
        value = self.dump_from(obj, self.name)
        value = self.format(value)
        return value

    def format(self, value):
        if self.formatter and value is not None:
            value = self.formatter(value)
        return value

    def load(self, data: dict):
        value = self.load_from(data)
        if value is None:
            if self.allow_none:
                return None
            else:
                raise ValidationError(self.error_messages.get('allow_none'))

        value = self.parse(value)
        self.validate(value)
        return value

    def load_from(self, data: dict):
        if self.key in data.keys():
            value = data[self.key]
            return value
        elif self.required:
            raise ValidationError(self.error_messages.get('required'))
        else:
            return None

    def validate(self, value):
        for validator in self.validators:
            validator(value)


class StringField(Field):
    def __init__(self, min_length=None, max_length=None,
                 formatter=str, parse=str, validators=None, **kwargs):
        self.min_length = min_length
        self.max_length = max_length
        if validators is None and \
                (min_length is not None or max_length is not None):
            validators = LengthValidator(min_length, max_length)
        super().__init__(
            formatter=formatter, parse=parse, validators=validators, **kwargs)


class NumberField(Field):
    type_ = float

    def __init__(self, min_value=None, max_value=None,
                 formatter=None, parse=None, validators=None, **kwargs):
        self.max_value = self.type_(
            max_value) if max_value is not None else max_value
        self.min_value = self.type_(
            min_value) if min_value is not None else min_value

        if not formatter:
            formatter = self.type_

        if not parse:
            parse = self.type_

        if validators is None and \
                (min_value is not None or max_value is not None):
            validators = ComparisonValidator(min_value, max_value)

        super().__init__(
            formatter=formatter, parse=parse, validators=validators, **kwargs)


class IntegerField(NumberField):
    type_ = int


class FloatField(NumberField):
    type_ = float


class BoolField(Field):
    def __init__(self, formatter=bool, parse=bool, validators=None,
                 error_messages=None, **kwargs):

        if not validators:
            validators = BoolValidator(error_messages)

        super().__init__(
            formatter=formatter, parse=parse, validators=validators,
            error_messages=error_messages, **kwargs)


class ListField(Field):
    default_error_messages = {
        'iterable': 'The field value is not Iterable.',
    }

    def __init__(self, item_field, **kwargs):
        self.item_field = item_field
        super().__init__(**kwargs)

    def format(self, list_):
        if isinstance(list_, Iterable):
            list_ = [self.item_field.format(item) for item in list_]
        return list_

    def load(self, data):
        list_ = self.load_from(data)
        if list_ is None:
            if self.allow_none:
                return None
            else:
                raise ValidationError(self.error_messages.get('allow_none'))

        if not isinstance(list_, Iterable):
            raise ValidationError(self.error_messages.get('iterable'))

        for i, value in enumerate(list_):
            value = self.item_field.parse(value)
            self.item_field.validate(value)
            list_[i] = value
        return list_


class CallableField(Field):
    def __init__(self, func_args: list = None, func_kwargs: dict = None,
                 formatter=None, no_load=True, **kwargs):

        self.func_args = func_args if func_args else []

        self.func_kwargs = func_kwargs if func_kwargs else {}

        super().__init__(formatter=formatter, no_load=no_load, **kwargs)

    def format(self, func):
        value = None
        if func is not None:
            value = func(*self.func_args, **self.func_kwargs)
        if self.formatter and value is not None:
            value = self.formatter(value)
        return value


class DatetimeField(Field):
    type_ = datetime

    def __init__(self, fmt=None, formatter=None,
                 parse=None, validators=None, **kwargs):

        self.fmt = fmt

        if not formatter:
            if fmt:
                formatter = lambda dt: self.type_.strftime(dt, fmt)
            else:
                formatter = lambda dt: self.type_.isoformat(dt)

        if not parse:
            if fmt:
                parse = self._get_parse(fmt)
            else:
                parse = lambda dt_str: self.type_.fromisoformat(dt_str)

        super().__init__(
            formatter=formatter, parse=parse, validators=validators, **kwargs)

    def _get_parse(self, fmt):
        parse = no_processing
        if self.type_ is datetime:
            parse = lambda dt_str: datetime.strptime(dt_str, fmt)
        elif self.type_ is date:
            parse = lambda dt_str: datetime.strptime(dt_str, fmt).date()
        elif self.type_ is time:
            parse = lambda dt_str: datetime.strptime(dt_str, fmt).time()
        return parse


class TimeField(DatetimeField):
    type_ = time


class DateField(DatetimeField):
    type_ = date


class NestField(Field):
    def __init__(self, catalyst, parse=None, validators=None, **kwargs):

        self.catalyst = catalyst

        if not parse:
            parse = self._get_parse(catalyst)

        super().__init__(parse=parse, validators=validators, **kwargs)

    def format(self, obj):
        value = self.catalyst.dump(obj)
        return value

    def _get_parse(self, catalyst):
        def parse(obj):
            r = catalyst.load(obj)
            if not r.is_valid:
                raise ValidationError(r)
            return r.valid_data
        return parse

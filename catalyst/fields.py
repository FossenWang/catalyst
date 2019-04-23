"Fields"

from typing import Callable, Dict, Any, Iterable
from datetime import datetime, time, date

from .utils import ErrorMessageMixin
from .validators import (
    ValidationError, LengthValidator, ComparisonValidator,
    BoolValidator
)


Name = str
Value = Any


def no_processing(value):
    return value


class Field(ErrorMessageMixin):
    default_error_messages = {
        'required': 'Missing data for required field.',
        'none': 'Field may not be None.'
    }

    def __init__(self,
                 name: str = None,
                 key: str = None,
                 formatter: Callable[[Value], Value] = None,
                 parse: Callable[[Value], Value] = None,
                 validators: Callable[[Value], None] = None,
                 required: bool = False,
                 allow_none: bool = False,
                 error_messages: dict = None,
                 no_dump: bool = False,
                 no_load: bool = False,
                 ):
        self.name = name
        self.key = key
        self.required = required
        self.allow_none = allow_none
        self.no_dump = no_dump
        self.no_load = no_load

        self.formatter = formatter if formatter else no_processing

        self.parse = parse if parse else no_processing

        self.set_validators(validators)

        self.collect_error_messages(error_messages)

    def set_formatter(self, formatter: Callable[[Value], Value]):
        self.formatter = formatter
        return formatter

    def set_parse(self, parse: Callable[[Value], Value]):
        self.parse = parse
        return parse

    def set_validators(self, validators: Iterable[Callable[[Value], None]]):
        if validators is None:
            self.validators = []
            return validators

        if isinstance(validators, Iterable):
            self.validators = validators
        else:
            self.validators = [validators]

        for v in self.validators:
            if not isinstance(v, Callable):
                raise TypeError('Param validators must be ether Callable or Iterable contained Callable.')

        return validators

    def add_validator(self, validator: Callable[[Value], None]):
        if not isinstance(validator, Callable):
            raise TypeError('Param validator must be Callable.')

        self.validators.append(validator)
        return validator

    def dump(self, value):
        if self.formatter and value is not None:
            value = self.formatter(value)
        return value

    def load(self, value):
        if value is None:
            if self.allow_none:
                return None
            raise ValidationError(self.error_messages.get('none'))

        value = self.parse(value)
        self.validate(value)
        return value

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

    def dump(self, list_):
        if isinstance(list_, Iterable):
            list_ = [self.item_field.dump(item) for item in list_]
        elif list_ is not None:
            raise ValueError(f'The value of "{self.name}" field is not Iterable.')
        return list_

    def load(self, list_):
        if list_ is None:
            if self.allow_none:
                return None
            raise ValidationError(self.error_messages.get('none'))

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

    def dump(self, func):
        value = None
        if func is not None:
            value = func(*self.func_args, **self.func_kwargs)
        if self.formatter and value is not None:
            value = self.formatter(value)
        return value


class DatetimeField(Field):
    type_ = datetime
    default_fmt = r'%Y-%m-%d %H:%M:%S.%f'

    def __init__(self, fmt=None, formatter=None,
                 parse=None, validators=None, **kwargs):

        self.fmt = fmt if fmt else self.default_fmt

        if not formatter:
            formatter = self._format

        if not parse:
            parse = self._parse

        super().__init__(
            formatter=formatter, parse=parse, validators=validators, **kwargs)

    def _format(self, dt):
        return self.type_.strftime(dt, self.fmt)

    def _parse(self, date_string):
        return datetime.strptime(date_string, self.fmt)


class TimeField(DatetimeField):
    type_ = time
    default_fmt = r'%H:%M:%S.%f'

    def _parse(self, date_string):
        return datetime.strptime(date_string, self.fmt).time()


class DateField(DatetimeField):
    type_ = date
    default_fmt = r'%Y-%m-%d'

    def _parse(self, date_string):
        return datetime.strptime(date_string, self.fmt).date()


class NestedField(Field):
    def __init__(self, catalyst, parse=None, validators=None, **kwargs):

        self.catalyst = catalyst

        if not parse:
            parse = self._get_parse(catalyst)

        super().__init__(parse=parse, validators=validators, **kwargs)

    def dump(self, value):
        value = self.catalyst.dump(value)
        return value

    def _get_parse(self, catalyst):
        def parse(obj):
            r = catalyst.load(obj)
            if not r.is_valid:
                raise ValidationError(r)
            return r
        return parse

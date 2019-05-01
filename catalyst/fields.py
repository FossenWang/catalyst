"Fields"

import json

from typing import Callable, Any, Iterable, Union
from datetime import datetime, time, date

from .utils import ErrorMessageMixin
from .exceptions import ValidationError
from .validators import (
    LengthValidator,
    ComparisonValidator,
    BoolValidator
)


FormatterType = ParserType = Callable[[Any], Any]

ValidatorType = Callable[[Any], None]

MultiValidator = Union[ValidatorType, Iterable[ValidatorType]]


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
                 formatter: FormatterType = None,
                 parser: ParserType = None,
                 validators: MultiValidator = None,
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

        self.parser = parser if parser else no_processing

        self.set_validators(validators)

        self.collect_error_messages(error_messages)

    def set_formatter(self, formatter: FormatterType):
        self.formatter = formatter
        return formatter

    def set_parser(self, parser: ParserType):
        self.parser = parser
        return parser

    def set_validators(self, validators: MultiValidator):
        if validators is None:
            self.validators = []
            return validators

        if isinstance(validators, Iterable):
            self.validators = validators
        else:
            self.validators = [validators]

        for v in self.validators:
            if not isinstance(v, Callable):
                raise TypeError(
                    'Param validators must be ether Callable or Iterable contained Callable.')

        return validators

    def add_validator(self, validator: ValidatorType):
        if not isinstance(validator, Callable):
            raise TypeError('Param validator must be Callable.')

        self.validators.append(validator)
        return validator

    def dump(self, value):
        if self.formatter and value is not None:
            value = self.formatter(value)
        return value

    def dump_to_json(self, value):
        value = self.dump(value)
        return json.dumps(value)

    def load(self, value):
        if value is None:
            if self.allow_none:
                return None
            self.error('none')

        value = self.parser(value)
        self.validate(value)
        return value

    def validate(self, value):
        for validator in self.validators:
            validator(value)


class StringField(Field):
    def __init__(self,
                 min_length: int = None,
                 max_length: int = None,
                 formatter: FormatterType = str,
                 parser: ParserType = str,
                 validators: MultiValidator = None,
                 **kwargs):
        self.min_length = min_length
        self.max_length = max_length
        if validators is None and \
                (min_length is not None or max_length is not None):
            validators = LengthValidator(min_length, max_length)
        super().__init__(
            formatter=formatter, parser=parser, validators=validators, **kwargs)


class NumberField(Field):
    type_ = float

    def __init__(self,
                 min_value: type_ = None,
                 max_value: type_ = None,
                 formatter: FormatterType = None,
                 parser: ParserType = None,
                 validators: MultiValidator = None,
                 **kwargs):
        self.max_value = self.type_(max_value) \
            if max_value is not None else max_value
        self.min_value = self.type_(min_value) \
            if min_value is not None else min_value

        if not formatter:
            formatter = self.type_

        if not parser:
            parser = self.type_

        if validators is None and \
                (min_value is not None or max_value is not None):
            validators = ComparisonValidator(min_value, max_value)

        super().__init__(
            formatter=formatter, parser=parser, validators=validators, **kwargs)


class IntegerField(NumberField):
    type_ = int


class FloatField(NumberField):
    type_ = float


class BoolField(Field):
    def __init__(self,
                 formatter: FormatterType = bool,
                 parser: ParserType = bool,
                 validators: MultiValidator = None,
                 error_messages: dict = None,
                 **kwargs):

        if not validators:
            validators = BoolValidator(error_messages)

        super().__init__(
            formatter=formatter, parser=parser, validators=validators,
            error_messages=error_messages, **kwargs)


class ListField(Field):
    default_error_messages = {
        'iterable': 'The field value is not Iterable.',
    }

    def __init__(self, item_field: Field, **kwargs):
        self.item_field = item_field
        super().__init__(**kwargs)

    def dump(self, list_: Iterable):
        if isinstance(list_, Iterable):
            list_ = [self.item_field.dump(item) for item in list_]
        elif list_ is not None:
            raise TypeError(
                f'The value of "{self.name}" field is not Iterable.')
        return list_

    def dump_to_json(self, list_: Iterable):
        text = ''
        if isinstance(list_, Iterable):
            for item in list_:
                value = self.item_field.dump_to_json(item)
                text += f'{value}, '
            text = '[' + text[:-2] + ']'
        elif list_ is None:
            text = 'null'
        else:
            raise TypeError(
                f'The value of "{self.name}" field is not Iterable.')
        return text

    def load(self, list_: Iterable):
        if list_ is None:
            if self.allow_none:
                return None
            self.error('none')

        if not isinstance(list_, Iterable):
            self.error('iterable')

        for i, value in enumerate(list_):
            value = self.item_field.parser(value)
            self.item_field.validate(value)
            list_[i] = value
        return list_


class CallableField(Field):
    def __init__(self,
                 func_args: list = None,
                 func_kwargs: dict = None,
                 formatter: FormatterType = None,
                 **kwargs):

        self.func_args = func_args if func_args else []

        self.func_kwargs = func_kwargs if func_kwargs else {}

        super().__init__(formatter=formatter, no_load=True, **kwargs)

    def dump(self, func: Callable):
        value = None

        if isinstance(func, Callable):
            value = func(*self.func_args, **self.func_kwargs)
        elif func is not None:
            raise TypeError(
                f'The value of "{self.name}" field is not Callable.')

        if self.formatter and value is not None:
            value = self.formatter(value)
        return value

    def set_args(self, *args, **kwargs):
        self.func_args = args
        self.func_kwargs = kwargs


class DatetimeField(Field):
    type_ = datetime
    default_fmt = r'%Y-%m-%d %H:%M:%S.%f'

    def __init__(self,
                 fmt: str = None,
                 formatter: FormatterType = None,
                 parser: ParserType = None,
                 validators: MultiValidator = None,
                 **kwargs):

        self.fmt = fmt if fmt else self.default_fmt

        if not formatter:
            formatter = self._format

        if not parser:
            parser = self._parse

        super().__init__(
            formatter=formatter, parser=parser, validators=validators, **kwargs)

    def _format(self, dt: type_):
        return self.type_.strftime(dt, self.fmt)

    def _parse(self, date_string: str):
        return datetime.strptime(date_string, self.fmt)


class TimeField(DatetimeField):
    type_ = time
    default_fmt = r'%H:%M:%S.%f'

    def _parse(self, date_string: str):
        return datetime.strptime(date_string, self.fmt).time()


class DateField(DatetimeField):
    type_ = date
    default_fmt = r'%Y-%m-%d'

    def _parse(self, date_string: str):
        return datetime.strptime(date_string, self.fmt).date()


class NestedField(Field):
    def __init__(self,
                 catalyst,
                 parser: ParserType = None,
                 validators: MultiValidator = None,
                 **kwargs):

        self.catalyst = catalyst

        if not parser:
            parser = self._get_parser(catalyst)

        super().__init__(parser=parser, validators=validators, **kwargs)

    def dump(self, value):
        value = self.catalyst.dump(value)
        return value

    def dump_to_json(self, value):
        value = self.catalyst.dump_to_json(value)
        return value

    def _get_parser(self, catalyst):
        def parser(obj):
            r = catalyst.load(obj)
            if not r.is_valid:
                raise ValidationError(r)
            return r
        return parser

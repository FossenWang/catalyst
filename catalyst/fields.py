"Fields"

from typing import Callable, Any, Iterable, Union
from datetime import datetime, time, date
from warnings import warn

from .utils import ErrorMessageMixin, missing
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

    default_formatter = staticmethod(no_processing)
    default_parser = staticmethod(no_processing)
    default_validators = None

    def __init__(self,
                 name: str = None,
                 key: str = None,
                 formatter: FormatterType = None,
                 format_none: bool = False,
                 dump_required: bool = None,
                 dump_default: Any = missing,
                 no_dump: bool = False,
                 parser: ParserType = None,
                 parse_none: bool = False,
                 allow_none: bool = True,
                 validators: MultiValidator = None,
                 load_required: bool = None,
                 load_default: Any = missing,
                 no_load: bool = False,
                 error_messages: dict = None,
                 ):
        # Warn of redundant arguments
        if dump_required is None:
            # Field is required when default is not set, otherwise not required.
            dump_required = dump_default is missing
        elif dump_required and dump_default is not missing:
            warn('Some args of Field may redundant, '
                 'if "dump_default" is set, "dump_required=True" has no effect.')

        if load_required is None:
            # Field is not required by default
            load_required = False
        elif load_required and load_default is not missing:
            warn('Some args of Field may redundant, '
                 'if "load_default" is set, "load_required=True" has no effect.')

        if not allow_none and parse_none:
            warn('Some args of Field may redundant, '
                 'if "allow_none" is false, "parse_none=True" has no effect.')

        self.name = name
        self.key = key

        # Arguments used for dumping
        self.formatter = formatter if formatter else self.default_formatter
        self.format_none = format_none
        self.dump_required = dump_required
        self.dump_default = dump_default
        self.no_dump = no_dump

        # Arguments used for loading
        self.parser = parser if parser else self.default_parser
        self.parse_none = parse_none
        self.allow_none = allow_none
        self.set_validators(validators if validators else self.default_validators)
        self.load_required = load_required
        self.load_default = load_default
        self.no_load = no_load

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
            if not callable(v):
                raise TypeError(
                    'Argument "validators" must be ether Callable '
                    'or Iterable which contained Callable.')

        return validators

    def add_validator(self, validator: ValidatorType):
        if not callable(validator):
            raise TypeError('Argument "validator" must be Callable.')

        self.validators.append(validator)
        return validator

    def dump(self, value):
        if value is None and not self.format_none:
            # don't pass value to formatter
            return value

        if self.formatter:
            value = self.formatter(value)
        return value

    def load(self, value):
        if value is None:
            if not self.allow_none:
                self.error('none')
            elif not self.parse_none:
                return None

        value = self.parser(value)
        self.validate(value)
        return value

    def validate(self, value):
        for validator in self.validators:
            validator(value)


class StringField(Field):
    default_formatter = str
    default_parser = str

    def __init__(self,
                 min_length: int = None,
                 max_length: int = None,
                 validators: MultiValidator = None,
                 **kwargs):
        self.min_length = min_length
        self.max_length = max_length
        if validators is None and \
                (min_length is not None or max_length is not None):
            validators = LengthValidator(min_length, max_length)
        super().__init__(validators=validators, **kwargs)


class NumberField(Field):
    type_ = float
    default_formatter = float
    default_parser = float

    def __init__(self,
                 min_value: float = None,
                 max_value: float = None,
                 validators: MultiValidator = None,
                 **kwargs):
        self.max_value = self.type_(max_value) \
            if max_value is not None else max_value
        self.min_value = self.type_(min_value) \
            if min_value is not None else min_value

        if validators is None and \
                (min_value is not None or max_value is not None):
            validators = ComparisonValidator(min_value, max_value)

        super().__init__(validators=validators, **kwargs)


class FloatField(NumberField):
    pass


class IntegerField(NumberField):
    type_ = int
    default_formatter = int
    default_parser = int


class BoolField(Field):
    default_formatter = bool
    default_parser = bool
    default_validators = BoolValidator()


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
                 **kwargs):
        self.func_args = func_args if func_args else []
        self.func_kwargs = func_kwargs if func_kwargs else {}
        super().__init__(no_load=True, **kwargs)

    def dump(self, func: Callable):
        value = None

        if callable(func):
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

    def __init__(self, fmt: str = None, **kwargs):
        self.fmt = fmt if fmt else self.default_fmt
        super().__init__(**kwargs)

    def default_formatter(self, dt: type_):
        return self.type_.strftime(dt, self.fmt)

    def default_parser(self, date_string: str):
        return datetime.strptime(date_string, self.fmt)


class TimeField(DatetimeField):
    type_ = time
    default_fmt = r'%H:%M:%S.%f'

    def default_parser(self, date_string: str):
        return datetime.strptime(date_string, self.fmt).time()


class DateField(DatetimeField):
    type_ = date
    default_fmt = r'%Y-%m-%d'

    def default_parser(self, date_string: str):
        return datetime.strptime(date_string, self.fmt).date()


class NestedField(Field):
    def __init__(self, catalyst, **kwargs):
        self.catalyst = catalyst
        super().__init__(**kwargs)

    def default_formatter(self, value):
        return self.catalyst.dump(value)

    def default_parser(self, value):
        return self.catalyst.load(value)

"Fields"

from typing import Callable, Any, Iterable, Union, Mapping, Sequence
from datetime import datetime, time, date
from warnings import warn

from .utils import ErrorMessageMixin, missing, no_processing
from .validators import (
    LengthValidator,
    ComparisonValidator,
    TypeValidator,
)


FormatterType = ParserType = Callable[[Any], Any]

ValidatorType = Callable[[Any], None]

MultiValidator = Union[ValidatorType, Iterable[ValidatorType]]


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
        self.set_formatter(formatter if formatter else self.default_formatter)
        self.format_none = format_none
        self.dump_required = dump_required
        self.dump_default = dump_default
        self.no_dump = no_dump

        # Arguments used for loading
        self.set_parser(parser if parser else self.default_parser)
        self.parse_none = parse_none
        self.allow_none = allow_none
        self.set_validators(validators if validators else self.default_validators)
        self.load_required = load_required
        self.load_default = load_default
        self.no_load = no_load

        self.collect_error_messages(error_messages)

    def set_formatter(self, formatter: FormatterType):
        if not callable(formatter):
            raise TypeError('Argument "formatter" must be Callable.')

        self.formatter = formatter
        return formatter

    def set_parser(self, parser: ParserType):
        if not callable(parser):
            raise TypeError('Argument "parser" must be Callable.')

        self.parser = parser
        return parser

    @staticmethod
    def ensure_validators(validators: MultiValidator):
        if validators is None:
            return []

        if not isinstance(validators, Iterable):
            validators = [validators]

        for v in validators:
            if not callable(v):
                raise TypeError(
                    'Argument "validators" must be ether Callable '
                    'or Iterable which contained Callable.')
        return validators

    def set_validators(self, validators: MultiValidator):
        self.validators = list(self.ensure_validators(validators))
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
    default_validators = [TypeValidator(str)]

    def __init__(self, min_length: int = None, max_length: int = None, **kwargs):
        super().__init__(**kwargs)
        if min_length is not None or max_length is not None:
            self.add_validator(LengthValidator(min_length, max_length))


class NumberField(Field):
    default_formatter = float
    default_parser = float
    default_validators = [TypeValidator(float)]

    def __init__(self, min_value=None, max_value=None, **kwargs):
        super().__init__(**kwargs)
        if min_value is not None or max_value is not None:
            self.add_validator(ComparisonValidator(min_value, max_value))


class FloatField(NumberField):
    pass


class IntegerField(NumberField):
    default_formatter = int
    default_parser = int
    default_validators = [TypeValidator(int)]


class BoolField(Field):
    default_formatter = bool
    default_parser = bool
    default_validators = [TypeValidator(bool)]


class ListField(Field):
    default_validators = [TypeValidator(Sequence)]

    def __init__(self, item_field: Field, **kwargs):
        self.item_field = item_field
        super().__init__(**kwargs)

    def default_formatter(self, value: Iterable):
        return [self.item_field.dump(item) for item in value]

    def default_parser(self, value):
        return [self.item_field.load(item) for item in value]


class CallableField(Field):
    default_validators = [TypeValidator(Callable)]

    def __init__(self,
                 func_args: Iterable = None,
                 func_kwargs: Mapping = None,
                 **kwargs):
        if func_args is None:
            func_args = tuple()
        if func_kwargs is None:
            func_kwargs = {}
        self.set_args(*func_args, **func_kwargs)
        kwargs.pop('no_load', None)
        super().__init__(no_load=True, **kwargs)

    def default_formatter(self, func: Callable):
        return func(*self.func_args, **self.func_kwargs)

    def set_args(self, *args, **kwargs):
        self.func_args = args
        self.func_kwargs = kwargs


class DatetimeField(Field):
    _type = datetime
    _default_fmt = r'%Y-%m-%d %H:%M:%S.%f'
    default_validators = [TypeValidator(datetime)]

    def __init__(self, fmt: str = None, min_time=None, max_time=None, **kwargs):
        self.fmt = fmt if fmt else self._default_fmt
        super().__init__(**kwargs)
        if min_time is not None or max_time is not None:
            self.add_validator(ComparisonValidator(min_time, max_time))

    def default_formatter(self, dt):
        return self._type.strftime(dt, self.fmt)

    def default_parser(self, date_string: str):
        return datetime.strptime(date_string, self.fmt)


class TimeField(DatetimeField):
    _type = time
    _default_fmt = r'%H:%M:%S.%f'
    default_validators = [TypeValidator(time)]

    def default_parser(self, date_string: str):
        return datetime.strptime(date_string, self.fmt).time()


class DateField(DatetimeField):
    _type = date
    _default_fmt = r'%Y-%m-%d'
    default_validators = [TypeValidator(date)]

    def default_parser(self, date_string: str):
        return datetime.strptime(date_string, self.fmt).date()


class NestedField(Field):    
    default_validators = [TypeValidator(Mapping)]

    def __init__(self, catalyst, **kwargs):
        self.catalyst = catalyst
        super().__init__(**kwargs)

    def default_formatter(self, value):
        return self.catalyst.dump(value)

    def default_parser(self, value):
        return self.catalyst.load(value, True).valid_data

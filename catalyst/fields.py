from decimal import Decimal
from typing import Callable, Any, Iterable, Union, Mapping, Hashable, Dict
from datetime import datetime, time, date

from .utils import (
    BaseResult, ErrorMessageMixin,
    missing, no_processing, bind_attrs,
)
from .validators import (
    LengthValidator,
    RangeValidator,
    RegexValidator,
)
from .exceptions import ValidationError, ExceptionType


FormatterType = ParserType = Callable[[Any], Any]

ValidatorType = Callable[[Any], None]

MultiValidator = Union[ValidatorType, Iterable[ValidatorType]]


class Field(ErrorMessageMixin):
    """Basic field class for converting objects.

    Instantiation params can set default values by class variables.

    :param name:
    :param key:
    :param formatter:
    :param parser:
    :param format_none:
    :param parse_none:
    :param dump_required:
    :param load_required:
    :param dump_default: If set, `dumo_required` has no effect.
    :param load_default: Similar to `dump_default`
    :param no_dump:
    :param no_load:
    :param validators:
    :param allow_none:
    :param error_messages: Keys {'required', 'none'}.
    """
    formatter = staticmethod(no_processing)
    parser = staticmethod(no_processing)
    format_none = False
    parse_none = False
    dump_required = True
    load_required = False
    dump_default = missing
    load_default = missing
    no_dump = False
    no_load = False
    validators = []
    allow_none = True
    error_messages = {
        'required': 'Missing data for required field.',
        'none': 'Field may not be None.',
    }

    def __init__(
            self,
            name: str = None,
            key: str = None,
            formatter: FormatterType = None,
            parser: ParserType = None,
            format_none: bool = None,
            parse_none: bool = None,
            dump_required: bool = None,
            load_required: bool = None,
            dump_default: Any = missing,
            load_default: Any = missing,
            no_dump: bool = None,
            no_load: bool = None,
            validators: MultiValidator = None,
            allow_none: bool = None,
            error_messages: Dict[str, str] = None,
            **kwargs):
        self.name = name
        self.key = key
        bind_attrs(
            self,
            format_none=format_none,
            parse_none=parse_none,
            dump_required=dump_required,
            load_required=load_required,
            no_dump=no_dump,
            no_load=no_load,
            allow_none=allow_none,
            **kwargs,
        )
        if dump_default is not missing:
            self.dump_default = dump_default
        if load_default is not missing:
            self.load_default = load_default
        if formatter is not None:
            self.set_formatter(formatter)
        if parser is not None:
            self.set_parser(parser)
        self.set_validators(validators if validators else self.validators)
        self.collect_error_messages(error_messages)

    def set_formatter(self, formatter: FormatterType):
        if not callable(formatter):
            raise TypeError('Argument `formatter` must be Callable.')
        setattr(self, 'formatter', formatter)
        return formatter

    def set_parser(self, parser: ParserType):
        if not callable(parser):
            raise TypeError('Argument `parser` must be Callable.')
        setattr(self, 'parser', parser)
        return parser

    @staticmethod
    def ensure_validators(validators: MultiValidator) -> list:
        if not isinstance(validators, Iterable):
            validators = [validators]

        for v in validators:
            if not callable(v):
                raise TypeError(
                    'Argument `validators` must be ether Callable '
                    'or Iterable which contained Callable.')
        return list(validators)

    def set_validators(self, validators: MultiValidator):
        self.validators = self.ensure_validators(validators)
        return validators

    def add_validator(self, validator: ValidatorType):
        if not callable(validator):
            raise TypeError('Argument `validator` must be Callable.')
        self.validators.append(validator)
        return validator

    def validate(self, value):
        if value is None:
            if self.allow_none:
                return None
            self.error('none')
        for validator in self.validators:
            validator(value)
        return value

    def format(self, value):
        if value is None and not self.format_none:
            return None
        value = self.formatter(value)
        return value

    def dump(self, value):
        self.validate(value)
        value = self.format(value)
        return value

    def parse(self, value):
        if value is None and not self.parse_none:
            return None
        value = self.parser(value)
        return value

    def load(self, value):
        value = self.parse(value)
        self.validate(value)
        return value


class StringField(Field):
    """String Field.

    :param min_length: The minimum length of the value.
    :param max_length: The maximum length of the value.
    :param regex: The regular expression that the value must match.
    :param error_messages: Keys {'too_small', 'too_large', 'no_match',
        'required', 'none'}.
    """
    formatter = str
    parser = str

    def __init__(
            self,
            min_length: int = None,
            max_length: int = None,
            regex: str = None,
            **kwargs):
        super().__init__(**kwargs)
        if min_length is not None or max_length is not None:
            self.add_validator(
                LengthValidator(min_length, max_length, self.error_messages))
        if regex:
            self.add_validator(
                RegexValidator(regex, self.error_messages))


class NumberField(Field):
    """Base class for number fields. Using RangeValidator for validating.

    :param minimum: Value must >= minimum, and `None` is equal to -∞.
    :param maximum: Value must <= maximum, and `None` is equal to +∞.
    :param error_messages: Keys {'too_small', 'too_large', 'required', 'none'}.
    """
    formatter = float
    parser = float

    def __init__(self, minimum=None, maximum=None, **kwargs):
        super().__init__(**kwargs)
        if minimum is not None or maximum is not None:
            self.add_validator(
                RangeValidator(minimum, maximum, error_messages=self.error_messages))


class FloatField(NumberField):
    """Float field.

    :param kwargs: Same as `Number` field.
    """


class IntegerField(NumberField):
    """Integer field.

    :param kwargs: Same as `Number` field.
    """
    formatter = int
    parser = int


class DecimalField(NumberField):
    """Field for converting `decimal.Decimal` object.

    :param scale: The number of digits to the right of the decimal point.
        If `None`, does not quantize the value.
    :param rounding: The rounding mode, for example `decimal.ROUND_UP`.
        If `None`, the rounding mode of the current thread's context is used.
    :param dump_as: Data type that the value is serialized to.
    :param kwargs: Same as `Number` field.
    """
    dump_as = str
    scale = None
    rounding = None
    exponent = None

    def __init__(
            self,
            scale: int = None,
            rounding: str = None,
            dump_as: type = None,
            **kwargs):
        super().__init__(
            scale=scale, rounding=rounding, dump_as=dump_as, **kwargs)
        if not callable(self.dump_as):
            raise TypeError('`dump_as` must be callable.')
        scale = self.scale
        if scale is not None:
            self.exponent = Decimal((0, (), -int(scale)))

    def to_decimal(self, value):
        if isinstance(value, float):
            value = str(value)
        value = Decimal(value)
        if self.exponent is not None and value.is_finite():
            value = value.quantize(self.exponent, rounding=self.rounding)
        return value

    def formatter(self, value):
        num = self.to_decimal(value)
        return self.dump_as(num)

    parser = to_decimal


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
        super().__init__(value_map=value_map, **kwargs)
        self.reverse_value_map = {
            raw: parsed
            for parsed, raw_values in self.value_map.items()
            for raw in raw_values
        }

    def formatter(self, value):
        if isinstance(value, Hashable):
            value = self.reverse_value_map.get(value, value)
        value = bool(value)
        return value

    parser = formatter


class DatetimeField(Field):
    """Field for converting `datetime.datetime` object.

    :param fmt: Format of the value. See `datetime` module for details.
    :param minimum: The minimum value.
    :param maximum: The maximum value.
    :param error_messages: Keys {'too_small', 'too_large', 'required', 'none'}.
    """
    type_ = datetime
    fmt = r'%Y-%m-%d %H:%M:%S.%f'

    def __init__(self, fmt: str = None, minimum=None, maximum=None, **kwargs):
        super().__init__(fmt=fmt, **kwargs)
        if minimum is not None or maximum is not None:
            self.add_validator(
                RangeValidator(minimum, maximum, self.error_messages))

    def formatter(self, dt):
        return self.type_.strftime(dt, self.fmt)

    def parser(self, value: str):
        return datetime.strptime(value, self.fmt)


class TimeField(DatetimeField):
    """Field for converting `datetime.time` object.

    :param kwargs: Same as `DatetimeField` field.
    """
    type_ = time
    fmt = r'%H:%M:%S.%f'

    def parser(self, value: str):
        return datetime.strptime(value, self.fmt).time()


class DateField(DatetimeField):
    """Field for converting `datetime.date` object.

    :param kwargs: Same as `DatetimeField` field.
    """
    type_ = date
    fmt = r'%Y-%m-%d'

    def parser(self, value: str):
        return datetime.strptime(value, self.fmt).date()


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

    def formatter(self, func: Callable):
        return func(*self.func_args, **self.func_kwargs)


class ListField(Field):
    """List field, handle list elements with another `Field`.
    In order to ensure proper data structure, `format_none` and `parse_none`
    are set to True by default.

    :param item_field: A `Field` instance. Its "dump_method" is used to
        format each list item, and "load_method" is used to parse item.
    :param dump_method: The method name of `item_field`.
    :param load_method: Same as `dump_method`.
    :param all_errors: Whether to collect errors for every list elements.
    :param except_exception: Which types of errors should be collected.
    """
    item_field: Field = None
    dump_method = 'format'
    load_method = 'load'
    all_errors = True
    except_exception = Exception
    format_none = True
    parse_none = True

    def __init__(
            self,
            item_field: Field = None,
            dump_method: str = None,
            load_method: str = None,
            all_errors: bool = None,
            **kwargs):
        super().__init__(
            item_field=item_field,
            dump_method=dump_method,
            load_method=load_method,
            all_errors=all_errors,
            **kwargs)
        if not isinstance(self.item_field, Field):
            raise TypeError('Argument `item_field` must be a `Field` instance')
        self.format_item = getattr(self.item_field, self.dump_method)
        self.parse_item = getattr(self.item_field, self.load_method)

    def formatter(self, value):
        return self._process_many(
            value, self.all_errors, self.format_item, self.except_exception)

    def parser(self, value):
        return self._process_many(
            value, self.all_errors, self.parse_item, self.except_exception)

    @staticmethod
    def _process_many(
            data: Iterable,
            all_errors: bool,
            process_one: Callable,
            except_exception: ExceptionType):
        valid_data, errors, invalid_data = [], {}, {}
        for i, item in enumerate(data):
            try:
                result = process_one(item)
                valid_data.append(result)
            except except_exception as e:
                if isinstance(e, ValidationError) and isinstance(e.msg, BaseResult):
                    # distribute nested data in BaseResult
                    valid_data.append(e.msg.valid_data)
                    errors[i] = e.msg.errors
                    invalid_data[i] = e.msg.invalid_data
                else:
                    errors[i] = e
                    invalid_data[i] = item
                if not all_errors:
                    break
        if errors:
            raise ValidationError(BaseResult(valid_data, errors, invalid_data))
        return valid_data


class NestedField(Field):
    """Nested field, handle one or more objects with `Catalyst`.
    In order to ensure proper data structure, `format_none` and `parse_none`
    are set to True by default.

    :param catalyst: A `Catalyst` instance.
    :param many: Whether to use load_many/dump_many.
    """
    catalyst = None
    many = False
    format_none = True
    parse_none = True

    def __init__(self, catalyst=None, many: bool = None, **kwargs):
        super().__init__(catalyst=catalyst, many=many, **kwargs)
        if self.many:
            self._do_dump = self.catalyst.dump_many
            self._do_load = self.catalyst.load_many
        else:
            self._do_dump = self.catalyst.dump
            self._do_load = self.catalyst.load

    def formatter(self, value):
        return self._do_dump(value, raise_error=True).valid_data

    def parser(self, value):
        return self._do_load(value, raise_error=True).valid_data

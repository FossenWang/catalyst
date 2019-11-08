import decimal
from typing import Callable, Any, Iterable, Union, Mapping, Hashable, Dict
from datetime import datetime, time, date

from .utils import (
    DumpResult, LoadResult, ErrorMessageMixin,
    missing, no_processing, OptionBox,
)
from .validators import (
    LengthValidator,
    RangeValidator,
    RegexValidator,
)
from .exceptions import ValidationError


FormatterType = ParserType = Callable[[Any], Any]

ValidatorType = Callable[[Any], None]

MultiValidator = Union[ValidatorType, Iterable[ValidatorType]]


class Field(ErrorMessageMixin):
    default_error_messages = {
        'required': 'Missing data for required field.',
        'none': 'Field may not be None.',
    }

    class Options(OptionBox):
        formatter = staticmethod(no_processing)
        format_none = False
        dump_required = True
        dump_default = missing
        no_dump = False

        parser = staticmethod(no_processing)
        parse_none = False
        load_required = False
        load_default = missing
        no_load = False

        validators = None  # type: list
        allow_none = True

    def __init__(
            self,
            name: str = None,
            key: str = None,
            formatter: FormatterType = None,
            format_none: bool = None,
            dump_required: bool = None,
            dump_default: Any = missing,
            no_dump: bool = None,
            parser: ParserType = None,
            parse_none: bool = None,
            load_required: bool = None,
            load_default: Any = missing,
            no_load: bool = None,
            validators: MultiValidator = None,
            allow_none: bool = None,
            error_messages: Dict[str, str] = None,
            **kwargs):
        """if `default` is set, `required` has no effect."""
        self.name = name
        self.key = key
        self.opts = self.Options(
            format_none=format_none,
            dump_required=dump_required,
            no_dump=no_dump,
            parse_none=parse_none,
            load_required=load_required,
            no_load=no_load,
            allow_none=allow_none,
            **kwargs,
        )
        if dump_default is not missing:
            self.opts.dump_default = dump_default
        if load_default is not missing:
            self.opts.load_default = load_default
        if formatter is not None:
            self.set_formatter(formatter)
        if parser is not None:
            self.set_parser(parser)
        self.set_validators(self.opts.get(validators=validators))
        self.collect_error_messages(error_messages)

    def set_formatter(self, formatter: FormatterType):
        if not callable(formatter):
            raise TypeError('Argument `formatter` must be Callable.')
        self.opts.formatter = formatter
        return formatter

    def set_parser(self, parser: ParserType):
        if not callable(parser):
            raise TypeError('Argument `parser` must be Callable.')
        self.opts.parser = parser
        return parser

    @staticmethod
    def ensure_validators(validators: MultiValidator) -> list:
        if validators is None:
            return []

        if not isinstance(validators, Iterable):
            validators = [validators]

        for v in validators:
            if not callable(v):
                raise TypeError(
                    'Argument `validators` must be ether Callable '
                    'or Iterable which contained Callable.')
        return list(validators)

    def set_validators(self, validators: MultiValidator):
        self.opts.validators = self.ensure_validators(validators)
        return validators

    def add_validator(self, validator: ValidatorType):
        if not callable(validator):
            raise TypeError('Argument `validator` must be Callable.')
        self.opts.validators.append(validator)
        return validator

    def validate(self, value):
        if value is None:
            if self.opts.allow_none:
                return None
            self.error('none')
        for validator in self.opts.validators:
            validator(value)
        return value

    def format(self, value):
        if value is None and not self.opts.format_none:
            return None
        value = self.opts.formatter(value)
        return value

    def dump(self, value):
        self.validate(value)
        value = self.format(value)
        return value

    def parse(self, value):
        if value is None and not self.opts.parse_none:
            return None
        value = self.opts.parser(value)
        return value

    def load(self, value):
        value = self.parse(value)
        self.validate(value)
        return value

    @property
    def dump_default(self):
        default = self.opts.dump_default
        if callable(default):
            default = default()
        return default

    @property
    def load_default(self):
        default = self.opts.load_default
        if callable(default):
            default = default()
        return default


class String(Field):
    class Options(Field.Options):
        formatter = str
        parser = str

    def __init__(
            self,
            max_length: int = None,
            min_length: int = None,
            regex: str = None,
            **kwargs):
        super().__init__(**kwargs)
        if min_length is not None or max_length is not None:
            self.add_validator(
                LengthValidator(min_length, max_length, self.error_messages))
        if regex:
            self.add_validator(
                RegexValidator(regex, self.error_messages))


class Number(Field):
    """Base class for number fields. Using RangeValidator for validating.

    :param minimum: Value must >= minimum, and `None` is equal to -∞.
    :param maximum: Value must <= maximum, and `None` is equal to +∞.
    :param error_messages: Keys `{'too_small', 'too_large'}`.
    """

    class Options(Field.Options):
        formatter = float
        parser = float

    def __init__(self, minimum=None, maximum=None, **kwargs):
        super().__init__(**kwargs)
        if minimum is not None or maximum is not None:
            self.add_validator(
                RangeValidator(minimum, maximum, error_messages=self.error_messages))


class Float(Number):
    """Float field.

    :param kwargs: Same as `Number` field.
    """


class Integer(Number):
    """Integer field.

    :param kwargs: Same as `Number` field.
    """
    class Options(Number.Options):
        formatter = int
        parser = int


class Decimal(Number):
    """Decimal field.

    :param kwargs: Same as `Number` field.
    """
    def __init__(self, to_string: bool = None, **kwargs):
        super().__init__(to_string=to_string, **kwargs)

    class Options(Number.Options):
        to_string = True

        @staticmethod
        def to_decimal(value):
            return decimal.Decimal(str(value))

        parser = to_decimal

        def formatter(self, value):
            num = self.to_decimal(value)
            if self.to_string:
                num = str(num)
            return num


class Boolean(Field):
    """Boolean field.

    :param value_map: Values that will be onverted to `True` or `False`.
        The keys are `True` and `False`, values are `Hashable`.
    """
    def __init__(self, value_map: dict = None, **kwargs):
        super().__init__(value_map=value_map, **kwargs)
        self.opts.reverse_value_map = {
            raw: parsed
            for parsed, raw_values in self.opts.value_map.items()
            for raw in raw_values
        }

    class Options(Field.Options):
        reverse_value_map = None  # type: dict
        value_map = {
            True: ('1', 'y', 'yes', 'true', 'True'),
            False: ('0', 'n', 'no', 'false', 'False'),
        }

        def parser(self, value):
            if isinstance(value, Hashable):
                value = self.reverse_value_map.get(value, value)
            value = bool(value)
            return value

        formatter = parser


class Datetime(Field):
    def __init__(self, fmt: str = None, min_time=None, max_time=None, **kwargs):
        super().__init__(fmt=fmt, **kwargs)
        if min_time is not None or max_time is not None:
            self.add_validator(
                RangeValidator(min_time, max_time, self.error_messages))

    class Options(Field.Options):
        type_ = datetime
        fmt = r'%Y-%m-%d %H:%M:%S.%f'

        def formatter(self, dt):
            return self.type_.strftime(dt, self.fmt)

        def parser(self, date_string: str):
            return datetime.strptime(date_string, self.fmt)


class Time(Datetime):
    class Options(Datetime.Options):
        type_ = time
        fmt = r'%H:%M:%S.%f'

        def parser(self, date_string: str):
            return datetime.strptime(date_string, self.fmt).time()


class Date(Datetime):
    class Options(Datetime.Options):
        type_ = date
        fmt = r'%Y-%m-%d'

        def parser(self, date_string: str):
            return datetime.strptime(date_string, self.fmt).date()


class Method(Field):
    def __init__(self, func_args: Iterable = None, func_kwargs: Mapping = None, **kwargs):
        kwargs.pop('no_load', None)
        super().__init__(no_load=True, **kwargs)
        func_args = self.opts.get(func_kwargs=func_args)
        func_kwargs = self.opts.get(func_kwargs=func_kwargs)
        self.set_args(*func_args, **func_kwargs)

    def set_args(self, *args, **kwargs):
        self.opts.func_args = args
        self.opts.func_kwargs = kwargs

    class Options(Field.Options):
        func_args = tuple()
        func_kwargs = {}

        def formatter(self, func: Callable):
            return func(*self.func_args, **self.func_kwargs)


class List(Field):
    def __init__(
            self,
            item_field: Field,
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

    class Options(Field.Options):
        item_field = None  # type: Field
        dump_method = 'format'
        load_method = 'load'
        all_errors = True

        def formatter(self, value: Iterable):
            return self._process_many('dump', value)

        def parser(self, value: Iterable):
            return self._process_many('load', value)

        def _process_many(self, name: str, data: Iterable):
            if name == 'dump':
                ResultClass = DumpResult
                method_name = self.dump_method
            elif name == 'load':
                ResultClass = LoadResult
                method_name = self.load_method
            else:
                raise ValueError("Argument `name` must be 'dump' or 'load'.")

            handle = getattr(self.item_field, method_name)
            all_errors = self.all_errors

            valid_data, errors, invalid_data = [], {}, {}
            for i, item in enumerate(data):
                try:
                    result = handle(item)
                    valid_data.append(result)
                except Exception as error:
                    errors[i] = error
                    invalid_data[i] = item
                    if not all_errors:
                        break

            if errors:
                raise ValidationError(ResultClass(valid_data, errors, invalid_data))
            return valid_data


class Nested(Field):
    def __init__(self, catalyst, **kwargs):
        super().__init__(catalyst=catalyst, **kwargs)

    class Options(Field.Options):
        catalyst = None

        def formatter(self, value):
            return self.catalyst.dump(value, True).valid_data

        def parser(self, value):
            return self.catalyst.load(value, True).valid_data

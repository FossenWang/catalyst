"""Field classes for various types of data."""

import decimal
import datetime
import inspect
from functools import partial

from typing import (
    Any, Iterable, Union, Mapping, Hashable, Dict,
    Callable as CallableType,
)

from .base import CatalystABC
from .utils import (
    BaseResult, ErrorMessageMixin, copy_keys,
    missing, no_processing, bind_attrs,
)
from .validators import (
    LengthValidator,
    RangeValidator,
    RegexValidator,
    MemberValidator,
    NonMemberValidator,
)
from .exceptions import ValidationError, ExceptionType


ValidatorType = CallableType[[Any], None]

MultiValidator = Union[ValidatorType, Iterable[ValidatorType]]


class BaseField(ErrorMessageMixin):
    """Basic field class for converting objects.

    Instantiation params can set default values by class variables.

    :param name: The source field to get the value from when dumping data.
        The target field to set the value to when loading data. For example,
        ``result[key] = field.dump(data[field.name])``, and
        ``result[name] = field.load(data[field.key])``.
    :param key: The source field to get the value from when loading data.
        The target field to set the value to when dumping data.
    :param no_dump: Whether to skip this field during dumping.
    :param no_load: Whether to skip this field during loading.
    :param error_messages: A dict of error messages.
    """
    no_dump = False
    no_load = False

    name: str
    key: str
    # Aliases for `name` and `key`
    dump_source = property(lambda self: self.name)
    dump_target = property(lambda self: self.key)
    load_source = property(lambda self: self.key)
    load_target = property(lambda self: self.name)

    def __init__(
            self,
            name: str = None,
            key: str = None,
            no_dump: bool = None,
            no_load: bool = None,
            error_messages: Dict[str, str] = None):
        self.name = name
        self.key = key
        self.collect_error_messages(error_messages)
        bind_attrs(self, no_dump=no_dump, no_load=no_load)

    def override_method(
            self, func: CallableType = None, attr: str = None,
            obj_name='field', original_name='original_method'):
        """Override a method of the field instance. Inject field instance or covered method
        as argments into the function according to argument name.

        Example:

            field.override_method(function, 'format')

            @field.override_method(attr='format')
            def function(value):
                return value

            field.set_format = field.override_method(attr='format')

            @field.set_format
            def function(self, value):
                return value

            @field.set_format
            def function(value, field, original_method):
                return original_method(value)

            @field.override_method(attr='format', obj_name='obj', original_name='old')
            def function(value, obj, old):
                return old(value)

        :param func: The function to override. The value will be passed to the first argument.
            Particularly, if the first argument is `self`, the field instance will be injected,
            and value will be the second argument.
            If argments like "field", "original_method" or "**kwargs" exist, the field instance
            or covered method will be passed.
        :param attr: The attribute to be overrided.
        :param obj_name: The argment name of the instence itself.
        :param original_name: The argment name of the original method.
        """
        if func is None:
            return partial(
                self.override_method, attr=attr,
                obj_name=obj_name, original_name=original_name)

        sig = inspect.signature(func)
        kwargs = {}
        # inject args if the last parameter is keyword arguments
        for param in reversed(sig.parameters.values()):
            if param.kind is inspect._VAR_KEYWORD:
                kwargs[obj_name] = self
                kwargs[original_name] = getattr(self, attr)
            break
        # inject args if parameter name matches
        if not kwargs:
            if obj_name in sig.parameters:
                kwargs[obj_name] = self
            if original_name in sig.parameters:
                kwargs[original_name] = getattr(self, attr)

        if sig.parameters:
            first_arg = next(iter(sig.parameters))
            # inject `self` if it's the first argment of `func`
            if first_arg == 'self':
                kwargs.pop('self', None)
                func = partial(func, self)

            # kwargs can't be first
            for arg_name in kwargs:
                if first_arg == arg_name:
                    raise TypeError(f'The first argment of "{func}" can not be "{arg_name}".')

        if kwargs:
            func = partial(func, **kwargs)

        setattr(self, attr, func)
        return func

    def dump(self, *args, **kwargs):
        raise NotImplementedError

    def load(self, *args, **kwargs):
        raise NotImplementedError


class Field(BaseField):
    """Handles only a single field value of the input data, and can not access
    the other field values. This does not process the value by default.

    :param formatter: The function that formats the field value during dumping,
        and which will override `Field.format`.
    :param parser: The function that parses the field value during loading,
        and which will override `Field.parse`.
    :param dump_required: Raise error if the field value doesn't exist.
    :param load_required: Similar to `dump_required`.
    :param dump_default: The default value when the field value doesn't exist.
        If set, `dump_required` has no effect.
        Particularly, the `missing` object means that this field will not exist
        in result, and `None` means that default value is `None`.
    :param load_default: Similar to `dump_default`.
    :param validators: Validator or collection of validators. The validator
        function is not required to return value, and should raise error
        directly if invalid.
        By default, validators are called during loading.
    :param allow_none: Whether the field value are allowed to be `None`.
        By default, this takes effect during loading.
    :param in_: A collection of valid values.
    :param not_in: A collection of invalid values.
    :param error_messages: Keys {'required', 'none', 'in', 'not_in'}.
    :param kwargs: Same as :class:`BaseField`.
    """
    dump_required = None
    load_required = None
    dump_default = missing
    load_default = missing
    validators = []
    allow_none = True
    error_messages = {
        'required': 'Missing data for required field.',
        'none': 'Field may not be None.',
    }

    def __init__(
            self,
            formatter: CallableType = None,
            parser: CallableType = None,
            dump_required: bool = None,
            load_required: bool = None,
            dump_default: Any = missing,
            load_default: Any = missing,
            validators: MultiValidator = None,
            allow_none: bool = None,
            in_: Iterable = None,
            not_in: Iterable = None,
            **kwargs):
        super().__init__(**kwargs)
        bind_attrs(
            self,
            dump_required=dump_required,
            load_required=load_required,
            allow_none=allow_none,
        )

        if dump_default is not missing:
            self.dump_default = dump_default
        if load_default is not missing:
            self.load_default = load_default
        if formatter is not None:
            self.set_format(formatter)
        if parser is not None:
            self.set_parse(parser)
        self.set_validators(validators if validators else self.validators)
        if in_:
            msg = self.error_messages.get('in')
            self.add_validator(MemberValidator(in_, msg))
        if not_in:
            msg = self.error_messages.get('not_in')
            self.add_validator(NonMemberValidator(not_in, msg))

    def set_format(self, func: CallableType = None, **kwargs):
        """Override `Field.format` method which will be called during dumping.
        See `BaseField.override_method` for more details.
        """
        return self.override_method(func, 'format', **kwargs)

    def set_parse(self, func: CallableType = None, **kwargs):
        """Override `Field.parse` method which will be called during loading.
        See `BaseField.override_method` for more details.
        """
        return self.override_method(func, 'parse', **kwargs)

    @staticmethod
    def ensure_validators(validators: MultiValidator) -> list:
        """Make sure validators are callables."""
        if not isinstance(validators, Iterable):
            validators = [validators]

        for v in validators:
            if not callable(v):
                raise TypeError(
                    'Argument "validators" must be ether Callable '
                    'or Iterable which contained Callable.')
        return list(validators)

    def set_validators(self, validators: MultiValidator):
        """Replace all validators."""
        self.validators = self.ensure_validators(validators)
        return validators

    def add_validator(self, validator: ValidatorType):
        """Append a validator to list."""
        if not callable(validator):
            raise TypeError('Argument "validator" must be Callable.')
        self.validators.append(validator)
        return validator

    def validate(self, value):
        """Validate `value`, raise error if it is invalid."""
        if value is None:
            if self.allow_none:
                return None
            raise self.error('none')
        for validator in self.validators:
            validator(value)
        return value

    validate_dump = staticmethod(no_processing)
    validate_load = validate

    def format(self, value):
        return value

    def dump(self, value):
        """Serialize `value` as native Python data type by validating and
        formatting. By default, it doesn't validate `value` during dumping,
        but you can override `validate_dump` method to perform validation.
        """
        self.validate_dump(value)
        value = self.format(value)
        return value

    def parse(self, value):
        return value

    def load(self, value):
        """Deserialize `value` to an object by parsing and validating."""
        value = self.parse(value)
        self.validate_load(value)
        return value


class ConstantField(Field):
    """Constant Field."""

    def __init__(self, constant, **kwargs):
        super().__init__(**kwargs)
        self.constant = constant
        self.dump_default = constant
        self.load_default = constant

    def format(self, value):
        return self.constant

    def parse(self, value):
        return self.constant


class StringField(Field):
    """String Field.

    :param min_length: The minimum length of the value.
    :param max_length: The maximum length of the value.
    :param regex: The regular expression that the value must match.
    :param error_messages: Keys {'too_small', 'too_large', 'not_between', 'no_match', ...}.
    """

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

    def format(self, value):
        if value is None:
            return value
        return str(value)

    parse = format


class NumberField(Field):
    """Base class for number fields.

    :param minimum: Value must >= minimum, and `None` is equal to -∞.
    :param maximum: Value must <= maximum, and `None` is equal to +∞.
    :param error_messages: Keys {'too_small', 'too_large', 'not_between', ...}.
    """
    obj_type = float

    def __init__(self, minimum=None, maximum=None, **kwargs):
        super().__init__(**kwargs)
        self.minimum = minimum
        self.maximum = maximum

        if minimum is not None or maximum is not None:
            msg_dict = copy_keys(self.error_messages, ('too_small', 'too_large', 'not_between'))
            self.add_validator(RangeValidator(minimum, maximum, msg_dict))

    def format(self, value):
        if value is None:
            return value
        return self.obj_type(value)

    parse = format


class FloatField(NumberField):
    """Float field.

    :param minimum: Value must >= minimum, and `None` is equal to -∞.
    :param maximum: Value must <= maximum, and `None` is equal to +∞.
    :param error_messages: Keys {'too_small', 'too_large', 'not_between', ...}.
    """


class IntegerField(NumberField):
    """Integer field.

    :param minimum: Value must >= minimum, and `None` is equal to -∞.
    :param maximum: Value must <= maximum, and `None` is equal to +∞.
    :param error_messages: Keys {'too_small', 'too_large', 'not_between', ...}.
    """
    obj_type = int


class DecimalField(NumberField):
    """Field for converting `decimal.Decimal` object.

    :param places: The number of digits to the right of the decimal point.
        If `None`, does not quantize the value.
    :param rounding: The rounding mode, for example `decimal.ROUND_UP`.
        If `None`, the rounding mode of the current thread's context is used.
    :param dump_as: Data type that the value is serialized to.
    :param minimum: Value must >= minimum, and `None` is equal to -∞.
    :param maximum: Value must <= maximum, and `None` is equal to +∞.
    :param error_messages: Keys {'too_small', 'too_large', 'not_between', ...}.
    """
    obj_type = decimal.Decimal
    dump_as = str
    places = None
    rounding = None
    exponent = None

    def __init__(
            self,
            places: int = None,
            rounding: str = None,
            dump_as: type = None,
            **kwargs):
        super().__init__(**kwargs)
        bind_attrs(self, places=places, rounding=rounding, dump_as=dump_as)

        if not callable(self.dump_as):
            raise TypeError('Argument "dump_as" must be callable.')
        if self.places is not None:
            self.exponent = decimal.Decimal((0, (), -int(self.places)))

    def to_decimal(self, value):
        if isinstance(value, float):
            value = str(value)
        value = decimal.Decimal(value)
        if self.exponent is not None and value.is_finite():
            value = value.quantize(self.exponent, rounding=self.rounding)
        return value

    def format(self, value):
        if value is None:
            return value
        num = self.to_decimal(value)
        return self.dump_as(num)

    def parse(self, value):
        if value is None:
            return value
        return self.to_decimal(value)


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
        if value is None:
            return value
        if isinstance(value, Hashable):
            value = self.reverse_value_map.get(value, value)
        return bool(value)

    parse = format


class DatetimeField(Field):
    """Field for converting `datetime.datetime` object.
    Only native formats of `datetime.strftime()` and `datetime.strptime()` are supported.

    Example:

        # Aware datetime
        field = DatetimeField(fmt=r'%Y-%m-%d %H:%M:%S%z')
        field.load('2000-01-01 00:00:00+0000')

        # Naive datetime
        field = DatetimeField(fmt=r'%Y-%m-%d %H:%M:%S.%f')
        field.load('2000-01-01 00:00:00.000000')

    :param fmt: Format of the value. See `datetime` module for details.
    :param minimum: The minimum value.
    :param maximum: The maximum value.
    :param error_messages: Keys {'too_small', 'too_large', 'not_between', ...}.
    """
    obj_type = datetime.datetime
    fmt = r'%Y-%m-%d %H:%M:%S'

    def __init__(self, fmt: str = None, minimum=None, maximum=None, **kwargs):
        super().__init__(**kwargs)
        bind_attrs(self, fmt=fmt)
        self.minimum = minimum
        self.maximum = maximum
        if minimum is not None or maximum is not None:
            msg_dict = copy_keys(self.error_messages, ('too_small', 'too_large', 'not_between'))
            self.add_validator(RangeValidator(minimum, maximum, msg_dict))

    def format(self, value):
        if value is None:
            return value
        return self.obj_type.strftime(value, self.fmt)

    def parse(self, value):
        # `load_default` might be a datetime object
        if value is None or isinstance(value, self.obj_type):
            return value
        return datetime.datetime.strptime(value, self.fmt)


class TimeField(DatetimeField):
    """Field for converting `datetime.time` object.

    :param kwargs: Same as `DatetimeField` field.
    """
    obj_type = datetime.time
    fmt = r'%H:%M:%S'

    def parse(self, value):
        if value is None or isinstance(value, self.obj_type):
            return value
        return datetime.datetime.strptime(value, self.fmt).time()


class DateField(DatetimeField):
    """Field for converting `datetime.date` object.

    :param kwargs: Same as `DatetimeField` field.
    """
    obj_type = datetime.date
    fmt = r'%Y-%m-%d'

    def parse(self, value: str):
        if value is None or isinstance(value, self.obj_type):
            return value
        return datetime.datetime.strptime(value, self.fmt).date()


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


class ListField(Field):
    """List field, handle list elements with another `Field`.
    In order to ensure proper data structure, `None` is not valid.

    :param item_field: A `Field` class or instance.
    :param min_length: The minimum length of the list.
    :param max_length: The maximum length of the list.
    :param all_errors: Whether to collect errors for every list elements.
    :param except_exception: Which types of errors should be collected.
    :param error_messages: Keys {'too_small', 'too_large', 'not_between', ...}.
    """
    item_field: Field = None
    all_errors = True
    except_exception = Exception
    allow_none = False

    def __init__(
            self,
            item_field: Field = None,
            min_length: int = None,
            max_length: int = None,
            all_errors: bool = None,
            except_exception=None,
            **kwargs):
        super().__init__(**kwargs)
        bind_attrs(
            self,
            item_field=item_field,
            all_errors=all_errors,
            except_exception=except_exception,
        )
        if min_length is not None or max_length is not None:
            msg_dict = copy_keys(self.error_messages, ('too_small', 'too_large', 'not_between'))
            self.add_validator(LengthValidator(min_length, max_length, msg_dict))

        item_field = self.item_field
        if not isinstance(item_field, Field):
            raise TypeError(f'Argument "item_field" must be a Field, not "{item_field}".')
        self.format_item = getattr(item_field, 'dump')
        self.parse_item = getattr(item_field, 'load')

    def format(self, value):
        return self._process_many(
            value, self.all_errors, self.format_item, self.except_exception)

    def parse(self, value):
        return self._process_many(
            value, self.all_errors, self.parse_item, self.except_exception)

    @staticmethod
    def _process_many(
            data: Iterable,
            all_errors: bool,
            process_one: CallableType,
            except_exception: ExceptionType):
        valid_data, errors, invalid_data = [], {}, {}
        for i, item in enumerate(data):
            try:
                result = process_one(item)
                valid_data.append(result)
            except except_exception as e:
                if isinstance(e, ValidationError) and isinstance(e.detail, BaseResult):
                    # distribute nested data in BaseResult
                    valid_data.append(e.detail.valid_data)
                    errors[i] = e.detail.errors
                    invalid_data[i] = e.detail.invalid_data
                else:
                    errors[i] = e
                    invalid_data[i] = item
                if not all_errors:
                    break
        if errors:
            result = BaseResult(valid_data, errors, invalid_data)
            raise ValidationError(msg=result.format_errors(), detail=result)
        return valid_data


class SeparatedField(ListField):
    """Field for convert between a separated string and a list of the words.

    :param separator: Argument for `str.split(sep=separator)` and `separator.join`.
        If separator is `None`, whitespace will be used to join words.
    :param maxsplit: Argument for `str.split(maxsplit=maxsplit)`.
    """
    separator = None
    maxsplit = -1

    def __init__(self, item_field: Field = None, separator=missing, maxsplit=None, **kwargs):
        super().__init__(item_field=item_field, **kwargs)
        bind_attrs(self, maxsplit=maxsplit)
        if separator is not missing:  # `None` is a valid value
            self.separator = separator

    def parse(self, value):
        value = value.split(self.separator, self.maxsplit)
        value = super().parse(value)
        return value

    def format(self, value):
        value = super().format(value)
        separator = self.separator or ' '
        value = separator.join(str(v) for v in value)
        return value


class NestedField(Field):
    """Nested field, handle one or more objects with `Catalyst`.
    In order to ensure proper data structure, `None` is not valid.

    :param catalyst: A `Catalyst` class or instance.
    :param many: Whether to process multiple objects.
    """
    catalyst: CatalystABC = None
    many = False
    allow_none = False

    def __init__(self, catalyst: CatalystABC = None, many: bool = None, **kwargs):
        super().__init__(**kwargs)
        bind_attrs(self, catalyst=catalyst, many=many)

        catalyst = self.catalyst
        if not isinstance(catalyst, CatalystABC):
            raise TypeError(f'Argument "catalyst" must be a Catalyst, not "{catalyst}".')
        if self.many:
            self._do_dump = catalyst.dump_many
            self._do_load = catalyst.load_many
        else:
            self._do_dump = catalyst.dump
            self._do_load = catalyst.load

    def format(self, value):
        return self._do_dump(value, raise_error=True).valid_data

    def parse(self, value):
        return self._do_load(value, raise_error=True).valid_data


# typing hint
FieldDict = Dict[str, BaseField]


# Aliases
Str = String = StringField
Bool = Boolean = BooleanField
Int = Integer = IntegerField
Float = FloatField
Decimal = DecimalField
Number = NumberField
Datetime = DatetimeField
Date = DateField
Time = TimeField
Callable = CallableField
List = ListField
Nested = NestedField
Constant = ConstantField
Separated = SeparatedField

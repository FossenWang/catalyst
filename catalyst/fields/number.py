import math
import decimal

from ..utils import copy_keys, bind_attrs
from ..validators import RangeValidator

from .base import Field


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
        return self.obj_type(value)

    parse = format


class IntegerField(NumberField):
    """Integer field.

    :param minimum: Value must >= minimum, and `None` is equal to -∞.
    :param maximum: Value must <= maximum, and `None` is equal to +∞.
    :param error_messages: Keys {'too_small', 'too_large', 'not_between', ...}.
    """
    obj_type = int


class FloatField(NumberField):
    """Float field.

    :param nan_to_none: If `True`, `NaN`, `Infinity` and `-Infinity` are converted to
        `dump_none` or `load_none`.
        If `False`, the special values are converted to string when dumping.
    :param minimum: Value must >= minimum, and `None` is equal to -∞.
    :param maximum: Value must <= maximum, and `None` is equal to +∞.
    :param error_messages: Keys {'too_small', 'too_large', 'not_between', ...}.
    """
    obj_type = float
    nan_to_none = True

    def __init__(self, nan_to_none: bool = None, **kwargs):
        super().__init__(**kwargs)
        bind_attrs(self, nan_to_none=nan_to_none)

    def format(self, value):
        value = self.obj_type(value)
        if not math.isfinite(value):
            if self.nan_to_none:
                value = self.dump_none
            else:
                value = str(value)
        return value

    def parse(self, value):
        value = self.obj_type(value)
        if self.nan_to_none and not math.isfinite(value):
            value = self.load_none
        return value


class DecimalField(FloatField):
    """Field for converting `decimal.Decimal` object.

    :param places: The number of digits to the right of the decimal point.
        If `None`, does not quantize the value.
    :param rounding: The rounding mode, for example `decimal.ROUND_UP`.
        If `None`, the rounding mode of the current thread's context is used.
    :param dump_as: Data type that the value is serialized to.
    :param nan_to_none: If `True`, `NaN`, `Infinity` and `-Infinity` are converted to
        `dump_none` or `load_none`.
        If `False`, the special values are converted to string when dumping.
    :param minimum: Value must >= minimum, and `None` is equal to -∞.
    :param maximum: Value must <= maximum, and `None` is equal to +∞.
    :param error_messages: Keys {'too_small', 'too_large', 'not_between', ...}.
    """
    obj_type = decimal.Decimal
    dump_as = str
    places = None
    rounding = None
    nan_to_none = True

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
        else:
            self.exponent = None

    def to_decimal(self, value):
        if isinstance(value, float):
            value = str(value)
        return decimal.Decimal(value)

    def quantize(self, value):
        if self.exponent is not None:
            value = value.quantize(self.exponent, rounding=self.rounding)
        return value

    def format(self, value):
        value = self.to_decimal(value)
        if value.is_finite():
            value = self.quantize(value)
        elif self.nan_to_none:
            return self.dump_none
        return self.dump_as(value)

    def parse(self, value):
        value = self.to_decimal(value)
        if value.is_finite():
            value = self.quantize(value)
        elif self.nan_to_none:
            return self.load_none
        return value

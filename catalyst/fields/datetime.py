import datetime

from ..utils import copy_keys, bind_attrs
from ..validators import RangeValidator

from .base import Field


class DatetimeField(Field):
    """Field for converting `datetime.datetime` object.
    Only native formats of `datetime.strftime()` and `datetime.strptime()` are supported.

    Example:

        # Aware datetime
        field = DatetimeField(fmt=r'%Y-%m-%d %H:%M:%S%z')
        field.load('2000-01-01 00:00:00+0000')

        # Naive datetime
        field = DatetimeField(fmt=r'%Y-%m-%d %H:%M:%S')
        field.load('2000-01-01 00:00:00')

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
        return self.obj_type.strftime(value, self.fmt)

    def parse(self, value):
        # `load_default` might be a datetime object
        if isinstance(value, self.obj_type):
            return value
        return datetime.datetime.strptime(value, self.fmt)


class TimeField(DatetimeField):
    """Field for converting `datetime.time` object.

    :param kwargs: Same as `DatetimeField` field.
    """
    obj_type = datetime.time
    fmt = r'%H:%M:%S'

    def parse(self, value):
        if isinstance(value, self.obj_type):
            return value
        return datetime.datetime.strptime(value, self.fmt).time()


class DateField(DatetimeField):
    """Field for converting `datetime.date` object.

    :param kwargs: Same as `DatetimeField` field.
    """
    obj_type = datetime.date
    fmt = r'%Y-%m-%d'

    def parse(self, value: str):
        if isinstance(value, self.obj_type):
            return value
        return datetime.datetime.strptime(value, self.fmt).date()

"Fields"

from typing import Callable, Dict
from collections import Iterable

from .validators import ValidationError, LengthValidator, ComparisonValidator, \
    BoolValidator


from_attribute = getattr

no_processing = lambda value: value


class Field:
    default_error_messages = {
        'required': 'Missing data for required field.',
        'allow_none': 'Field may not be None.'
    }

    def __init__(self, name: str=None, key: str=None, source: Callable=None, formatter: Callable=None,
                 validator: Callable=None, before_validate: Callable=None, after_validate: Callable=None,
                 required=False, allow_none=True, error_messages: Dict[str]=None):
        self.name = name
        self.key = key
        self.required = required
        self.allow_none = allow_none

        self.source = source if source else from_attribute

        self.formatter = formatter if formatter else no_processing

        self.before_validate = before_validate if before_validate else no_processing

        self.validator = validator if validator else no_processing

        self.after_validate = after_validate if after_validate else no_processing

        self.error_messages = self.default_error_messages.copy() \
            if self.default_error_messages else {}
        self.error_messages.update(error_messages if error_messages else {})

        # 待定参数: default

    def set_source(self, source):
        self.source = source
        return source

    def set_formatter(self, formatter):
        self.formatter = formatter
        return formatter

    def set_before_validate(self, before_validate):
        self.before_validate = before_validate
        return before_validate

    def set_validator(self, validator):
        self.validator = validator
        return validator

    def set_after_validate(self, after_validate):
        self.after_validate = after_validate
        return after_validate

    def set_serialize(self, serialize):
        self.serialize = serialize
        return serialize

    def set_deserialize(self, deserialize):
        self.deserialize = deserialize
        return deserialize

    def serialize(self, obj):
        value = self.source(obj, self.name)
        if self.formatter and value is not None:
            value = self.formatter(value)
        return value

    def get_deserializing_value(self, data: dict):
        if self.key in data.keys():
            value = data[self.key]
            return value
        elif self.required:
            raise ValidationError(self.error_messages.get('required'))
        else:
            return None

    def deserialize(self, data):
        value = self.get_deserializing_value(data)
        if value is None:
            if self.allow_none:
                return None
            else:
                raise ValidationError(self.error_messages.get('allow_none'))

        value = self.before_validate(value)
        self.validate(value)
        value = self.after_validate(value)
        return value

    def validate(self, value):
        if isinstance(self.validator, Iterable):
            for vld in self.validator:
                vld(value)
        else:
            self.validator(value)


class StringField(Field):

    def __init__(self, name=None, key=None, source=None, formatter=str,
                 before_validate=str, validator=None, after_validate=None,
                 required=False, allow_none=True, error_messages=None,
                 min_length=None, max_length=None):
        self.min_length = min_length
        self.max_length = max_length
        if validator is None and \
            (min_length is not None or max_length is not None):
            validator = LengthValidator(min_length, max_length)

        super().__init__(
            name=name, key=key, source=source, formatter=formatter,
            before_validate=before_validate, validator=validator, after_validate=after_validate,
            required=required, allow_none=allow_none, error_messages=error_messages
            )


class NumberField(Field):
    type_ = float

    def __init__(self, name=None, key=None, source=None, formatter=None,
                 before_validate=None, validator=None, after_validate=None,
                 required=False, allow_none=True, error_messages=None,
                 min_value=None, max_value=None):
        self.max_value = self.type_(max_value) if max_value is not None else max_value
        self.min_value = self.type_(min_value) if min_value is not None else min_value

        if not formatter:
            formatter = self.type_

        if not before_validate:
            before_validate = self.type_

        if validator is None and \
            (min_value is not None or max_value is not None):
            validator = ComparisonValidator(min_value, max_value)

        super().__init__(
            name=name, key=key, source=source, formatter=formatter,
            before_validate=before_validate, validator=validator, after_validate=after_validate,
            required=required, allow_none=allow_none, error_messages=error_messages
            )


class IntegerField(NumberField):
    type_ = int


class FloatField(NumberField):
    type_ = float


class BoolField(Field):

    def __init__(self, name=None, key=None, source=None, formatter=bool,
                 before_validate=bool, validator=None, after_validate=None,
                 required=False, allow_none=True, error_messages=None):

        if not validator:
            validator = BoolValidator(error_messages)

        super().__init__(
            name=name, key=key, source=source, formatter=formatter,
            before_validate=before_validate, validator=validator, after_validate=after_validate,
            required=required, allow_none=allow_none, error_messages=error_messages
            )


class ListFormatter:
    def __init__(self, item_field):
        self.item_field = item_field

    def __call__(self, list_):
        for i, val in enumerate(list_):
            list_[i] = self.item_field.formatter(val)
        return list_


class ListField(Field):
    item_field = Field()

    def __init__(self, name=None, key=None, source=None, formatter=None,
                 validator=None, before_validate=None, after_validate=None,
                 required=False, allow_none=True, error_messages=None, item_field=None):

        if item_field:
            self.item_field = item_field

        if not formatter:
            formatter = ListFormatter(item_field)

        self.default_error_messages['iterable'] = 'The field value is not Iterable.',

        super().__init__(
            name=name, key=key, source=source, formatter=formatter,
            before_validate=before_validate, validator=validator, after_validate=after_validate,
            required=required, allow_none=allow_none, error_messages=error_messages
            )

    def deserialize(self, data):
        list_ = self.get_deserializing_value(data)
        if list_ is None:
            if self.allow_none:
                return None
            else:
                raise ValidationError(self.error_messages.get('allow_none'))

        if not isinstance(list_, Iterable):
            raise ValidationError(self.error_messages.get('iterable'))

        for i, value in enumerate(list_):
            value = self.item_field.before_validate(value)
            self.item_field.validate(value)
            value = self.item_field.after_validate(value)
            list_[i] = value
        return list_


class CallableFormatter:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __call__(self, func):
        return func(*self.args, **self.kwargs)


def call_func(func):
    return func()


class CallableField(Field):
    def __init__(self, name=None, key=None, source=None, formatter=None,
                 validator=None, before_validate=None, after_validate=None,
                 required=False, allow_none=True, error_messages=None,
                 func_args: list=None, func_kwargs: dict=None):

        if not func_args:
            func_args = []

        if not func_kwargs:
            func_kwargs={}

        if not formatter:
            formatter = CallableFormatter(*func_args, **func_kwargs)

        super().__init__(
            name=name, key=key, source=source, formatter=formatter,
            before_validate=before_validate, validator=validator, after_validate=after_validate,
            required=required, allow_none=allow_none, error_messages=error_messages
            )

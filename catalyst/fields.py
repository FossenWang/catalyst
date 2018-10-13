"Fields"

from .validators import StringValidator, IntegerValidator, FloatValidator, \
    BooleanValidator


from_attribute = getattr

class Field:
    def __init__(self, name=None, key=None, source=from_attribute,
                 formatter=None, validator=None, required=False):
        self.name = name
        self.key = key
        self.source = source
        self.formatter = formatter
        self.validator = validator
        self.required = required
        # 待定参数: default

    def extract(self, obj):
        value = self.source(obj, self.name)
        if self.formatter:
            value = self.formatter(value)
        return value

    def validate(self, value):
        if self.validator:
            value = self.validator(value)
        return value


class StringField(Field):
    def __init__(self, name=None, key=None, source=from_attribute,
                 formatter=str, validator=None, required=False,
                 min_length=None, max_length=None):
        self.min_length = min_length
        self.max_length = max_length
        if validator is None and \
            (min_length is not None or max_length is not None):
            validator = StringValidator(min_length, max_length)

        super().__init__(name=name, key=key, source=source,
            formatter=formatter, validator=validator, required=required)


class NumberField(Field):
    type_ = None
    validator_class = None

    def __init__(self, name=None, key=None, source=from_attribute,
                 formatter=None, validator=None, required=False,
                 min_value=None, max_value=None):
        self.max_value = max_value
        self.min_value = min_value

        if not formatter:
            formatter = self.type_

        if validator is None and \
            (min_value is not None or max_value is not None):
            validator = self.validator_class(min_value, max_value)

        super().__init__(name=name, key=key, source=source,
            formatter=formatter, validator=validator, required=required)


class IntegerField(NumberField):
    type_ = int
    validator_class = IntegerValidator


class FloatField(NumberField):
    type_ = float
    validator_class = FloatValidator


class BoolField(Field):
    def __init__(self, name=None, key=None, source=from_attribute,
                 formatter=bool, validator=None, required=False):
        if not validator:
            validator = BooleanValidator()

        super().__init__(name=name, key=key, source=source,
            formatter=formatter, validator=validator, required=required)

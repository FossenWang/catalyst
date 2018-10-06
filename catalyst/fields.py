"Fields"

from .validators import StringValidator, IntegerValidator

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
                 max_length=None, min_length=None):
        self.max_length = max_length
        self.min_length = min_length
        if validator is None and \
            (max_length is not None or min_length is not None):
            validator = StringValidator(max_length, min_length)

        super().__init__(name=name, key=key, source=source,
            formatter=formatter, validator=validator, required=required)


class IntegerField(Field):
    def __init__(self, name=None, key=None, source=from_attribute,
                 formatter=int, validator=None, required=False,
                 max_value=None, min_value=None):
        self.max_value = max_value
        self.min_value = min_value
        if validator is None and \
            (max_value is not None or min_value is not None):
            validator = IntegerValidator(max_value, min_value)

        super().__init__(name=name, key=key, source=source,
            formatter=formatter, validator=validator, required=required)


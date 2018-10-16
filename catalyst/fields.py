"Fields"

from .validators import LengthValidator, ComparisonValidator, \
    BoolValidator, ValidationError


from_attribute = getattr

no_processing = lambda value: value

class Field:
    parse_error_message = None

    def __init__(self, name=None, key=None, source=None,
                 formatter=None, validator=None, required=False,
                 parser=None, parse_error_message=None, allow_none=True):
        self.name = name
        self.key = key
        if source:
            self.source = source
        else:
            self.source = from_attribute

        if formatter:
            self.formatter = formatter
        else:
            self.formatter = no_processing

        if parser:
            self.parser = parser
        else:
            self.parser = no_processing
        self.validator = validator
        self.required = required
        self.allow_none = allow_none
        if parse_error_message:
            self.parse_error_message = parse_error_message
        # 待定参数: default

    def serialize(self, obj):
        value = self.source(obj, self.name)
        if self.formatter and value is not None:
            value = self.formatter(value)
        return value

    def get_deserializing_value(self, data):
        if self.key in data.keys():
            value = data[self.key]
            return value
        elif self.required:
            raise ValidationError("Missing data for required field '%s'." % self.key)
        else:
            return None

    def deserialize(self, data):
        value = self.get_deserializing_value(data)
        if value is None:
            if self.allow_none:
                return None
            else:
                raise ValidationError('Field value can not be none.')

        value = self.parse(value)
        self.validate(value)
        return value

    def validate(self, value):
        if self.validator:
            self.validator(value)

    def parse(self, value):
        try:
            if self.parser:
                value = self.parser(value)
        except Exception as e:
            raise ValidationError(self.parse_error_message \
                if self.parse_error_message \
                else "Can't parse value: %s" % str(e))
        return value


class StringField(Field):
    parse_error_message = 'Ensure value is string or can be converted to a string'

    def __init__(self, name=None, key=None, source=None,
                 formatter=str, validator=None, required=False,
                 parser=str, parse_error_message=None, allow_none=True,
                 min_length=None, max_length=None, error_messages=None):
        self.min_length = min_length
        self.max_length = max_length
        if validator is None and \
            (min_length is not None or max_length is not None):
            validator = LengthValidator(min_length, max_length, error_messages)

        super().__init__(name=name, key=key, source=source,
            formatter=formatter, validator=validator, required=required,
            parser=parser, parse_error_message=parse_error_message,
            allow_none=allow_none)


class NumberField(Field):
    type_ = None

    def __init__(self, name=None, key=None, source=None,
                 formatter=None, validator=None, required=False,
                 parser=None, parse_error_message=None, allow_none=True,
                 min_value=None, max_value=None, error_messages=None):
        self.max_value = max_value
        self.min_value = min_value

        if not formatter:
            formatter = self.type_

        if not parser:
            parser = self.type_

        if not parse_error_message:
            parse_error_message = 'Ensure value is or can be converted to %s' % self.type_

        if validator is None and \
            (min_value is not None or max_value is not None):
            validator = ComparisonValidator(min_value, max_value)

        super().__init__(name=name, key=key, source=source,
            formatter=formatter, validator=validator, required=required,
            parser=parser, parse_error_message=parse_error_message,
            allow_none=allow_none)


class IntegerField(NumberField):
    type_ = int

class FloatField(NumberField):
    type_ = float


class BoolField(Field):
    parse_error_message = 'Ensure value is or can be converted to bool'

    def __init__(self, name=None, key=None, source=None,
                 formatter=bool, validator=None, required=False,
                 parser=bool, parse_error_message=None,  allow_none=True,
                 error_messages=None):

        if not validator:
            validator = BoolValidator(error_messages)

        super().__init__(name=name, key=key, source=source,
            formatter=formatter, validator=validator, required=required,
            parser=parser, parse_error_message=parse_error_message,
            allow_none=allow_none)

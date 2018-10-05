

class ValidationResult:
    def __init__(self, valid_data, errors, invalid_data):
        self.valid_data = valid_data
        self.is_valid = not errors
        self.errors = errors
        self.invalid_data = invalid_data


class ValidationError(Exception):
    pass


def from_attribute(obj, name):
    return getattr(obj, name)


class Field:
    def __init__(self, name=None, key=None, source=from_attribute,
                 formatter=None, validator=None, required=False):
        self.name = name
        self.key = key
        self.source = source
        self.formatter = formatter
        self.validator = validator
        self.requird = required

    def extract(self, obj):
        value = self.source(obj, self.name)
        if self.formatter:
            value = self.formatter(value)
        return value

    def validate(self, value):
        if self.validator:
            value = self.validator(value)
        return value

class StringValidator:
    def __init__(self, max_length=None, min_length=None, allow_blank=False):
        self.max_length = max_length
        self.min_length = min_length
        self.allow_blank = allow_blank

    def __call__(self, value):
        value = str(value)
        if not self.allow_blank and value == '':
            raise ValidationError("Ensure string is not empty")
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError("Ensure string length <= %d" % self.max_length)
        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError("Ensure string length >= %d" % self.min_length)
        return value


class StringField(Field):
    def __init__(self, name=None, key=None, source=from_attribute,
                 formatter=str, validator=None, required=False,
                 max_length=None, min_length=None, allow_blank=False):
        if validator is None and \
            (max_length is not None or min_length is not None):
            validator = StringValidator(max_length, min_length, allow_blank)

        super().__init__(name=name, key=key, source=source,
            formatter=formatter, validator=validator, required=required)


class Catalyst:
    def __init__(self, fields):
        # 之后应用元类收集
        self.fields = fields  # type: dict

    def extract(self, obj):
        obj_dict = {}
        for field in self.fields.values():
            # key和name的默认值需要用别的办法设置
            obj_dict[field.key] = field.extract(obj)
        return obj_dict

    def validate(self, data):
        invalid_data = {}
        valid_data = {}
        errors = {}
        for field in self.fields.values():
            value = data[field.key]
            try:
                value = field.validate(value)
            except Exception as e:
                errors[field.key] = e
                invalid_data[field.key] = value
            else:
                valid_data[field.key] = value
        return ValidationResult(valid_data, errors, invalid_data)




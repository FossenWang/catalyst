"Validators"


class ValidationResult:
    def __init__(self, valid_data, errors, invalid_data):
        self.valid_data = valid_data
        self.is_valid = not errors
        self.errors = errors
        self.invalid_data = invalid_data


class ValidationError(Exception):
    pass


class Validator:
    def __call__(self, value):
        raise NotImplementedError('Validate the given value and \
            return the valid value or raise any exception if invalid')


class StringValidator(Validator):
    'string validator'
    def __init__(self, max_length=None, min_length=None):
        self.max_length = max_length
        self.min_length = min_length

    def __call__(self, value):
        value = str(value)
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError("Ensure string length <= %d" % self.max_length)
        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError("Ensure string length >= %d" % self.min_length)
        return value


class IntegerValidator(Validator):
    'integer validator'
    def __init__(self, max_value, min_value):
        self.max_value = max_value
        self.min_value = min_value

    def __call__(self, value):
        value = int(value)
        if self.max_value is not None and value > self.max_value:
            raise ValidationError("Ensure value <= %d" % self.max_value)
        if self.min_value is not None and value < self.min_value:
            raise ValidationError("Ensure value >= %d" % self.min_value)
        return value

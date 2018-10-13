"Validators"


class ValidationResult:
    def __init__(self, valid_data, errors, invalid_data):
        self.valid_data = valid_data
        self.is_valid = not errors
        self.errors = errors
        self.invalid_data = invalid_data

    def __repr__(self):
        return 'ValidationResult(is_valid=%s, errors=%s)' % (self.is_valid, str(self.errors))


class ValidationError(Exception):
    pass


class Validator:
    """
    default_error_msg
    """
    default_error_msg = None

    def __init__(self, error_msg=None):
        """
        params:
        error_msg  type: dict
        stores msg of errors raised by validator
        change the dict data to custom error msg
        data will update a copy of default_error_msg
        """
        self.error_msg = self.default_error_msg.copy() if self.default_error_msg else {}
        self.error_msg.update(error_msg if error_msg else {})

    def __call__(self, value):
        raise NotImplementedError('Validate the given value and \
            return the valid value or raise any exception if invalid')


class StringValidator(Validator):
    """string validator"""
    def __init__(self, min_length=None, max_length=None, error_msg=None):
        self.min_length = min_length
        self.max_length = max_length

        if self.default_error_msg is None:
            self.default_error_msg = {
                'wrong_type': 'Ensure value is string or can be converted to a string',
                'too_small': "Ensure string length >= %d" % self.min_length,
                'too_large': "Ensure string length <= %d" % self.max_length,
            }
        super().__init__(error_msg=error_msg)

    def __call__(self, value):
        try:
            value = str(value)
        except Exception:
            raise ValidationError(self.error_msg['wrong_type'])

        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError(self.error_msg['too_small'])
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError(self.error_msg['too_large'])
        return value


class NumberValidator(Validator):
    """
    compare number
    error_msg:
    includ keys ('wrong_type', 'too_small', 'too_large')
    """
    name = None
    type_ = None

    def __init__(self, min_value=None, max_value=None, error_msg=None):
        self.min_value = min_value
        self.max_value = max_value

        if self.default_error_msg is None:
            self.default_error_msg = {
                'wrong_type': 'Ensure value is %s' % self.name,
                'too_small': "Ensure value >= %d" % self.min_value,
                'too_large': "Ensure value <= %d" % self.max_value,
            }

        super().__init__(error_msg=error_msg)

    def __call__(self, value):
        try:
            value = self.type_(value)
        except (TypeError, ValueError):
            raise ValidationError(self.error_msg['wrong_type'])

        if self.min_value is not None and value < self.min_value:
            raise ValidationError(self.error_msg['too_small'])

        if self.max_value is not None and value > self.max_value:
            raise ValidationError(self.error_msg['too_large'])
        return value


class IntegerValidator(NumberValidator):
    """integer validator"""
    name = 'integer'
    type_ = int


class FloatValidator(NumberValidator):
    """float validator"""
    name = 'float'
    type_ = float


class BooleanValidator(Validator):
    """bool validator"""
    default_error_msg = {
        'wrong_type': 'Ensure value is bool or can be converted to a bool',
    }

    def __init__(self, error_msg=None):
        super().__init__(error_msg=error_msg)

    def __call__(self, value):
        try:
            value = bool(value)
        except Exception:
            raise ValidationError(self.error_msg['wrong_type'])
        return value

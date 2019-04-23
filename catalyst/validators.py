"Validators"


class ValidationError(Exception):
    def __init__(self, msg, *args):
        self.msg = msg
        super().__init__(*args)

    def __repr__(self):
        return 'ValidationError(%s)' % repr(self.msg)

    def __str__(self):
        return str(self.msg)


class Validator:
    """
    default_error_messages
    """
    default_error_messages = {}

    def __init__(self, error_messages=None):
        """
        params:
        error_messages  type: dict
        stores msg of errors raised by validator
        change the dict data to custom error msg
        data will update a copy of default_error_messages
        """
        # Collect default error message from self and parent classes
        messages = {}
        for cls in reversed(self.__class__.__mro__):
            messages.update(getattr(cls, 'default_error_messages', {}))
        messages.update(error_messages or {})
        self.error_messages = messages

    def __call__(self, value):
        raise NotImplementedError('Validate the given value and \
            return the valid value or raise any exception if invalid')


class LengthValidator(Validator):
    """length validator"""
    def __init__(self, min_length=None, max_length=None, error_messages=None):
        self.min_length = min_length
        self.max_length = max_length

        if error_messages is None:
            error_messages = {}
        if min_length is not None:
            error_messages['too_small'] = "Ensure string length >= %d" % min_length
        if max_length is not None:
            error_messages['too_large'] = "Ensure string length <= %d" % max_length
        super().__init__(error_messages=error_messages)

    def __call__(self, value):
        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError(self.error_messages['too_small'])

        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError(self.error_messages['too_large'])


class ComparisonValidator(Validator):
    """
    comparison validator
    error_messages:
    includ keys ('too_small', 'too_large')
    """

    def __init__(self, min_value=None, max_value=None, error_messages=None):
        self.min_value = min_value
        self.max_value = max_value

        if error_messages is None:
            error_messages = {}
        if min_value is not None:
            error_messages['too_small'] = "Ensure value >= %d" % min_value
        if max_value is not None:
            error_messages['too_large'] = "Ensure value <= %d" % max_value
        super().__init__(error_messages=error_messages)

    def __call__(self, value):
        if self.min_value is not None and value < self.min_value:
            raise ValidationError(self.error_messages['too_small'])

        if self.max_value is not None and value > self.max_value:
            raise ValidationError(self.error_messages['too_large'])


class BoolValidator(Validator):
    """bool validator"""
    default_error_messages = {
        'type_error': 'Ensure value is bool',
    }

    def __init__(self, error_messages=None):
        super().__init__(error_messages=error_messages)

    def __call__(self, value):
        if not isinstance(value, bool):
            raise ValidationError(self.error_messages['type_error'])

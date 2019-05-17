"Validators"

from numbers import Number

from .utils import ErrorMessageMixin


class Validator(ErrorMessageMixin):
    def __init__(self, error_messages: dict = None):
        self.collect_error_messages(error_messages)

    def __call__(self, value):
        raise NotImplementedError((
            'Implement this method, return nothing if valid, '
            'or raise any exception if invalid.'))


class LengthValidator(Validator):
    """length validator"""

    def __init__(self,
                 min_length: int = None,
                 max_length: int = None,
                 error_messages: dict = None):
        if min_length is not None and max_length is not None \
            and min_length > max_length:
            raise ValueError('"min_length" can\'t be greater than "max_length".')

        self.min_length = min_length
        self.max_length = max_length

        error_messages = error_messages or {}
        if min_length is not None:
            error_messages.setdefault('too_small', f'Ensure string length >= {min_length}.')
        if max_length is not None:
            error_messages.setdefault('too_large', f'Ensure string length <= {max_length}.')
        super().__init__(error_messages=error_messages)

    def __call__(self, value):
        if self.min_length is not None and len(value) < self.min_length:
            self.error('too_small')

        if self.max_length is not None and len(value) > self.max_length:
            self.error('too_large')


class ComparisonValidator(Validator):
    """
    Compares between values.
    error_messages:
    includ keys ('too_small', 'too_large')
    """

    def __init__(self,
                 min_value: Number = None,
                 max_value: Number = None,
                 error_messages: dict = None):
        if min_value is not None and max_value is not None \
            and min_value > max_value:
            raise ValueError('"min_value" can\'t be greater than "max_value".')

        self.min_value = min_value
        self.max_value = max_value

        error_messages = error_messages or {}
        if min_value is not None:
            error_messages.setdefault('too_small', f'Ensure value >= {min_value}.')
        if max_value is not None:
            error_messages.setdefault('too_large', f'Ensure value <= {max_value}.')
        super().__init__(error_messages=error_messages)

    def __call__(self, value):
        if self.min_value is not None and value < self.min_value:
            self.error('too_small')

        if self.max_value is not None and value > self.max_value:
            self.error('too_large')


class BoolValidator(Validator):
    """bool validator"""
    default_error_messages = {
        'type_error': 'Ensure value is bool',
    }

    def __call__(self, value):
        if not isinstance(value, bool):
            self.error('type_error')

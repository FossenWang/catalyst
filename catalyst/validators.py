"""Validators"""

from .utils import ErrorMessageMixin, ERROR_MESSAGES


class Validator(ErrorMessageMixin):
    def __init__(self, error_messages: dict = None):
        self.collect_error_messages(error_messages)

    def __call__(self, value):
        raise NotImplementedError((
            'Implement this method, return nothing if valid, '
            'or raise any exception if invalid.'))


class LengthValidator(Validator):
    """
    Compares length between values.

    :param error_messages: includ keys {'too_short', 'too_long'}
    """
    error_messages = {}

    def __init__(
            self,
            min_length: int = None,
            max_length: int = None,
            error_messages: dict = None):
        if min_length is not None and max_length is not None \
            and min_length > max_length:
            raise ValueError('`min_length` can\'t be greater than `max_length`.')

        self.min_length = min_length
        self.max_length = max_length
        super().__init__(error_messages)

    def __call__(self, value):
        if self.min_length is not None and len(value) < self.min_length:
            self.error('too_short')

        if self.max_length is not None and len(value) > self.max_length:
            self.error('too_long')

ERROR_MESSAGES[LengthValidator] = {
    'too_short': 'Ensure length >= {self.min_length}.',
    'too_long': 'Ensure length <= {self.max_length}.',
}


class ComparisonValidator(Validator):
    """Compare between values.

    :param error_messages: includ keys {'too_small', 'too_large'}
    """
    def __init__(
            self,
            min_value=None,
            max_value=None,
            error_messages: dict = None):
        if min_value is not None and max_value is not None \
            and min_value > max_value:
            raise ValueError('`min_value` can\'t be greater than `max_value`.')

        self.min_value = min_value
        self.max_value = max_value
        super().__init__(error_messages)

    def __call__(self, value):
        if self.min_value is not None and value < self.min_value:
            self.error('too_small')

        if self.max_value is not None and value > self.max_value:
            self.error('too_large')

ERROR_MESSAGES[ComparisonValidator] = {
    'too_small': 'Ensure value >= {self.min_value}.',
    'too_large': 'Ensure value <= {self.max_value}.',
}


class TypeValidator(Validator):
    """Check type of value.

    :param error_messages: includ keys {'wrong_type'}
    """
    def __init__(self, class_or_tuple, error_messages: dict = None):
        self.class_or_tuple = class_or_tuple
        super().__init__(error_messages)

    def __call__(self, value):
        if not isinstance(value, self.class_or_tuple):
            error = self.get_error('wrong_type')
            raise TypeError(error.msg)

ERROR_MESSAGES[TypeValidator] = {
    'wrong_type': 'Type must be {self.class_or_tuple}.',
}

import re
from typing import Dict

from .utils import ErrorMessageMixin


class Validator(ErrorMessageMixin):
    """Check whether value is valid.

    :param error_messages: see `catalyst.utils.ErrorMessageMixin`.
    """
    def __init__(self, error_messages: Dict[str, str] = None):
        self.collect_error_messages(error_messages)

    def __call__(self, value):
        raise NotImplementedError((
            'Implement this method, return nothing if valid, '
            'or raise any exception if invalid.'))


class RangeValidator(Validator):
    """Check the passed value whether it is greater than
    or equal to `minimum` and less than or equal to `maximum`.

    :param minimum: Value must >= minimum, and `None` is equal to -∞.
    :param maximum: Value must <= maximum, and `None` is equal to +∞.
    :param error_messages: Keys `{'too_small', 'too_large'}`
    """
    error_messages = {
        'too_small': 'Value must >= {self.minimum}.',
        'too_large': 'Value must <= {self.maximum}.',
    }

    def __init__(self, minimum=None, maximum=None, error_messages: Dict[str, str] = None):
        if minimum is not None and maximum is not None \
            and minimum > maximum:
            raise ValueError('`minimum` can\'t be greater than `maximum`.')

        self.minimum = minimum
        self.maximum = maximum
        super().__init__(error_messages)

    def __call__(self, value):
        if self.minimum is not None and value < self.minimum:
            self.error('too_small')

        if self.maximum is not None and value > self.maximum:
            self.error('too_large')


class LengthValidator(RangeValidator):
    """
    Check length of the passed value.

    :param minimum: Value must >= minimum, and `None` is equal to -∞.
    :param maximum: Value must <= maximum, and `None` is equal to +∞.
    :param error_messages: Keys `{'too_small', 'too_large'}`.
    """
    error_messages = {
        'too_small': 'Length must >= {self.minimum}.',
        'too_large': 'Length must <= {self.maximum}.',
    }

    def __call__(self, value):
        super().__call__(len(value))


class TypeValidator(Validator):
    """Check type of value.

    :param class_or_tuple: Same as `isinstance` function's argument.
    :param error_messages: Keys `{'wrong_type'}`.
    """
    error_messages = {
        'wrong_type': 'Type must be {self.class_or_tuple}.',
    }

    def __init__(self, class_or_tuple, error_messages: Dict[str, str] = None):
        self.class_or_tuple = class_or_tuple
        super().__init__(error_messages)

    def __call__(self, value):
        if not isinstance(value, self.class_or_tuple):
            error = self.get_error('wrong_type')
            raise TypeError(error.msg)


class RegexValidator(Validator):
    """Check if string match regex pattern.

    :param regex: Regex pattern.
    :param error_messages: Keys `{'no_match'}`.
    """
    error_messages = {
        'no_match': 'No match for pattern "{self.regex.pattern}".',
    }

    def __init__(self, regex: str, error_messages: Dict[str, str] = None):
        self.regex = re.compile(regex)
        super().__init__(error_messages)

    def __call__(self, string: str):
        match = self.regex.search(string)
        if not match:
            self.error('no_match')
        return match

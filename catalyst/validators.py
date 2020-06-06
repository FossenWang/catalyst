import re
from typing import Dict, Iterable, Callable

from .exceptions import ValidationError
from .utils import ErrorMessageMixin, bind_attrs


class Validator:
    """Check whether value is valid.

    :param validate: A callable to check the value.
        If the value is valid, return True, else False.
    :param error_message: Error message to raise if invalid.
        Can be interpolated with `{self}` and `{value}`.
    """
    error_cls = ValidationError
    error_message = 'Invalid value.'

    def __init__(self, validate: Callable = None, error_message: str = None):
        bind_attrs(self, validate=validate, error_message=error_message)

    def validate(self, value):
        """If the value is valid, return True, else False."""
        return value

    def __call__(self, value):
        if not self.validate(value):
            raise self.error_cls(self.error_message.format(self=self, value=value))


class TypeValidator(Validator):
    """Check type of the value.

    :param class_or_tuple: Same as `isinstance` function's argument.
    """
    error_cls = TypeError
    error_message = 'Type must be {self.class_or_tuple}, not {value.__class__}.'

    def __init__(self, class_or_tuple, error_message: str = None):
        self.class_or_tuple = class_or_tuple
        super().__init__(None, error_message)

    def validate(self, value):
        return isinstance(value, self.class_or_tuple)


class RegexValidator(Validator):
    """Check if string match regex pattern.

    :param regex: Regex pattern.
    """
    error_message = 'No match for pattern "{self.regex.pattern}".'

    def __init__(self, regex: str, error_message: str = None):
        self.regex = re.compile(regex)
        super().__init__(None, error_message)

    def validate(self, value):
        return self.regex.search(value)


class MemberValidator(Validator):
    """Valid if the value is a member of `choices`.

    :param choices: A collection of valid values.
    """
    error_message = 'Must be one of {self.choices}.'

    def __init__(self, choices: Iterable, error_message: str = None):
        self.choices = choices
        super().__init__(None, error_message)

    def validate(self, value):
        return value in self.choices


class NonMemberValidator(MemberValidator):
    """Invalid if the value is a member of `choices`.

    :param choices: A collection of invalid values.
    """
    error_message = 'Can not be one of {self.choices}.'

    def validate(self, value):
        return value not in self.choices


class RangeValidator(ErrorMessageMixin, Validator):
    """Check the value whether it is greater than or equal to `minimum`,
    and less than or equal to `maximum`.

    :param minimum: Value must >= minimum, and `None` is equal to -∞.
    :param maximum: Value must <= maximum, and `None` is equal to +∞.
    :param error_messages: Keys {'too_small', 'too_large', 'not_between'}.
    """
    error_messages = {
        'too_small': 'Value must >= {self.minimum}.',
        'too_large': 'Value must <= {self.maximum}.',
        'not_between': 'Value must be between {self.minimum} and {self.maximum}.',
    }

    def __init__(self, minimum=None, maximum=None, error_messages: Dict[str, str] = None):
        self.collect_error_messages(error_messages)

        if minimum is not None and maximum is None:
            validate = self.check_minimum
            error_message = self.error_messages['too_small']

        elif minimum is None and maximum is not None:
            validate = self.check_maximum
            error_message = self.error_messages['too_large']

        elif minimum is not None and maximum is not None:
            if minimum > maximum:
                raise ValueError('"minimum" cannot be greater than "maximum".')

            validate = self.check_between
            error_message = self.error_messages['not_between']

        else:
            validate = self.infinite
            error_message = None

        self.minimum = minimum
        self.maximum = maximum
        super().__init__(validate, error_message)

    def check_minimum(self, value):
        return value >= self.minimum

    def check_maximum(self, value):
        return value <= self.maximum

    def check_between(self, value):
        return self.minimum <= value <= self.maximum

    def infinite(self, value):
        return True


class LengthValidator(RangeValidator):
    """Check length of the value.

    :param minimum: Value must >= minimum, and `None` is equal to -∞.
    :param maximum: Value must <= maximum, and `None` is equal to +∞.
    :param error_messages: Keys {'too_small', 'too_large', 'not_between'}.
    """
    error_messages = {
        'too_small': 'Length must >= {self.minimum}.',
        'too_large': 'Length must <= {self.maximum}.',
        'not_between': 'Length must be between {self.minimum} and {self.maximum}.',
    }

    def __call__(self, value):
        super().__call__(len(value))


# Aliases
Assert = Validator
Range = RangeValidator
Length = LengthValidator
Type = TypeValidator
Regex = RegexValidator
OneOf = MemberValidator
NoneOf = NonMemberValidator

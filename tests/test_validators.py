from unittest import TestCase
from unittest.mock import patch

from catalyst.exceptions import ValidationError
from catalyst.validators import (
    Validator,
    LengthValidator,
    RangeValidator,
    TypeValidator,
    RegexValidator,
    MemberValidator,
    NonMemberValidator,
)


class ValidationTest(TestCase):
    def test_base_validator(self):
        validator = Validator()
        validator(True)
        with self.assertRaises(ValidationError):
            validator(False)

        # test validate and error_message
        validator = Validator(validate=lambda x: x == 1, error_message='wrong')
        validator(1)
        with self.assertRaises(ValidationError) as cm:
            validator(0)
        self.assertEqual(str(cm.exception), 'wrong')

    @patch.dict('catalyst.validators.RangeValidator.error_messages')
    def test_range_validator(self):
        validator = RangeValidator()
        validator(None)

        validator = RangeValidator(maximum=1)
        validator(0)
        validator(1)
        with self.assertRaises(ValidationError):
            validator(2)

        RangeValidator.error_messages.update({'too_small': 'too_small'})
        validator = RangeValidator(0)
        with self.assertRaises(ValidationError) as cm:
            validator(-1)
        self.assertEqual(str(cm.exception), 'too_small')

        validator = RangeValidator(0, 100, error_messages={'not_between': 'not_between'})
        validator(1)
        validator(0)
        validator(100)
        with self.assertRaises(ValidationError) as cm:
            validator(101)
        self.assertEqual(str(cm.exception), 'not_between')
        with self.assertRaises(TypeError):
            validator('1')
        with self.assertRaises(TypeError):
            validator([1])

    @patch.dict('catalyst.validators.LengthValidator.error_messages')
    def test_length_validator(self):
        LengthValidator.error_messages.update({'too_small': 'too_small'})
        validator = LengthValidator(2)
        with self.assertRaises(ValidationError) as cm:
            validator('x')
        self.assertEqual(str(cm.exception), 'too_small')

        validator = LengthValidator(2, 10, error_messages={'not_between': 'not_between'})

        validator('x' * 2)
        validator('x' * 5)
        validator('x' * 10)
        validator(['xzc', 1])
        with self.assertRaises(ValidationError) as cm:
            validator('x' * 11)
        self.assertEqual(str(cm.exception), 'not_between')
        with self.assertRaises(ValidationError):
            validator('')
        with self.assertRaises(TypeError):
            validator(None)

        validator = LengthValidator(0, 1)
        validator('')
        validator([])

        validator = LengthValidator(minimum=1)
        with self.assertRaises(ValidationError):
            validator('')
        validator('1')

        validator = LengthValidator(maximum=2)
        with self.assertRaises(ValidationError):
            validator('123')
        validator('1')

        with self.assertRaises(ValueError):
            LengthValidator(1, 0)

    def test_type_validator(self):
        validator = TypeValidator(int)
        validator(0)
        with self.assertRaises(TypeError):
            validator('')

        validator = TypeValidator((int, str))
        validator(0)
        validator('')
        with self.assertRaises(TypeError):
            validator(0.0)

    def test_regex_validator(self):
        validator = RegexValidator('a')

        validator('cat')
        with self.assertRaises(TypeError):
            validator(None)

        with self.assertRaises(ValidationError):
            validator('dog')

        with self.assertRaises(TypeError):
            validator = RegexValidator(None)

    def test_member_validator(self):
        choices = {1, 2, 3}

        validator = MemberValidator(choices)
        validator(1)
        with self.assertRaises(ValidationError):
            validator(0)

        validator = NonMemberValidator(choices)
        validator(0)
        with self.assertRaises(ValidationError):
            validator(1)

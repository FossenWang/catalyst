from unittest import TestCase
from unittest.mock import patch

from catalyst.exceptions import ValidationError
from catalyst.utils import ERROR_MESSAGES
from catalyst.validators import (
    Validator, LengthValidator,
    RangeValidator, TypeValidator,
    RegexValidator,
)


class ValidationTest(TestCase):

    @patch.dict('catalyst.utils.ERROR_MESSAGES')
    def test_base_validator(self):
        with self.assertRaises(NotImplementedError):
            Validator()(None)

        class NewValidator(Validator):
            def __call__(self, value):
                self.error('msg')

        ERROR_MESSAGES.update({
            NewValidator: {'msg': 'default'}
        })

        # test alterable error messages
        default_validator = NewValidator()
        custom_msg_validator = NewValidator(error_messages={'msg': 'custom'})

        with self.assertRaises(ValidationError) as c:
            default_validator(0)
        self.assertEqual(str(c.exception), 'default')
        with self.assertRaises(ValidationError) as c:
            custom_msg_validator(0)
        self.assertEqual(str(c.exception), 'custom')
        self.assertEqual(repr(c.exception), "ValidationError('custom')")

    @patch.dict('catalyst.utils.ERROR_MESSAGES')
    def test_range_validator(self):
        ERROR_MESSAGES[RangeValidator].update({'too_small': 'too_small'})
        compare_integer = RangeValidator(0, 100, {'too_large': 'too_large'})
        compare_integer(1)
        compare_integer(0)
        compare_integer(100)
        with self.assertRaises(ValidationError) as c:
            compare_integer(-1)
        self.assertEqual(str(c.exception), 'too_small')
        with self.assertRaises(ValidationError) as c:
            compare_integer(101)
        self.assertEqual(str(c.exception), 'too_large')
        with self.assertRaises(TypeError):
            compare_integer('1')
        with self.assertRaises(TypeError):
            compare_integer([1])

        compare_integer_float = RangeValidator(-1.1, 1.1)

        compare_integer_float(1)
        compare_integer_float(0)
        compare_integer_float(0.1)
        compare_integer_float(1.1)
        compare_integer_float(-1.1)
        with self.assertRaises(ValidationError):
            compare_integer_float(-2)
        with self.assertRaises(ValidationError):
            compare_integer_float(2)
        with self.assertRaises(TypeError):
            compare_integer_float('1.1')
        with self.assertRaises(TypeError):
            compare_integer_float([1.1])

        with self.assertRaises(ValueError):
            RangeValidator(1, 0)

    @patch.dict('catalyst.utils.ERROR_MESSAGES')
    def test_length_validator(self):
        ERROR_MESSAGES[LengthValidator].update({'too_small': 'too_small'})
        validator = LengthValidator(2, 10, {'too_large': 'too_large'})

        validator('x' * 2)
        validator('x' * 5)
        validator('x' * 10)
        validator(['xzc', 1])
        with self.assertRaises(ValidationError) as c:
            validator('x')
        self.assertEqual(str(c.exception), 'too_small')
        with self.assertRaises(ValidationError) as c:
            validator('x' * 11)
        self.assertEqual(str(c.exception), 'too_large')
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

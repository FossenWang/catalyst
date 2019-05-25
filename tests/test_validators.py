from unittest import TestCase

from catalyst.exceptions import ValidationError
from catalyst.validators import (
    Validator, LengthValidator,
    ComparisonValidator
)


class ValidationTest(TestCase):

    def test_base_validator(self):
        with self.assertRaises(NotImplementedError):
            Validator()(None)

        class NewValidator(Validator):
            default_error_messages = {'msg': 'default'}
            def __call__(self, value):
                raise ValidationError(self.error_messages['msg'])

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

        self.assertDictEqual(NewValidator.default_error_messages, {'msg': 'default'})

    def test_comparison_validator(self):
        compare_integer = ComparisonValidator(0, 100)
        compare_integer(1)
        compare_integer(0)
        compare_integer(100)
        with self.assertRaises(ValidationError):
            compare_integer(-1)
        with self.assertRaises(ValidationError):
            compare_integer(101)
        with self.assertRaises(TypeError):
            compare_integer('1')
        with self.assertRaises(TypeError):
            compare_integer([1])

        compare_integer_float = ComparisonValidator(-1.1, 1.1)

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
            ComparisonValidator(1, 0)

    def test_length_validator(self):
        validator = LengthValidator(2, 10)

        validator('x' * 2)
        validator('x' * 5)
        validator('x' * 10)
        validator(['xzc', 1])
        with self.assertRaises(ValidationError):
            validator('x')
        with self.assertRaises(ValidationError):
            validator('x' * 11)
        with self.assertRaises(ValidationError):
            validator('')
        with self.assertRaises(TypeError):
            validator(None)

        validator = LengthValidator(0, 1)
        validator('')
        validator([])

        validator = LengthValidator(min_length=1)
        with self.assertRaises(ValidationError):
            validator('')
        validator('1')

        validator = LengthValidator(max_length=2)
        with self.assertRaises(ValidationError):
            validator('123')
        validator('1')

        with self.assertRaises(ValueError):
            LengthValidator(1, 0)

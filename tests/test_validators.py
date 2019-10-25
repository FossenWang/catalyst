from unittest import TestCase

from catalyst.exceptions import ValidationError
from catalyst.utils import ERROR_MESSAGES
from catalyst.validators import (
    Validator, LengthValidator,
    ComparisonValidator, TypeValidator
)


class ValidationTest(TestCase):

    def test_base_validator(self):
        with self.assertRaises(NotImplementedError):
            Validator()(None)

        class NewValidator(Validator):
            def __call__(self, value):
                raise ValidationError(self.error_messages['msg'])

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

    def test_comparison_validator(self):
        ERROR_MESSAGES[ComparisonValidator].update({'too_small': 'too_small'})
        compare_integer = ComparisonValidator(0, 100, {'too_large': 'too_large'})
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
        ERROR_MESSAGES[LengthValidator].update({'too_short': 'too_short'})
        validator = LengthValidator(2, 10, {'too_long': 'too_long'})

        validator('x' * 2)
        validator('x' * 5)
        validator('x' * 10)
        validator(['xzc', 1])
        with self.assertRaises(ValidationError) as c:
            validator('x')
        self.assertEqual(str(c.exception), 'too_short')
        with self.assertRaises(ValidationError) as c:
            validator('x' * 11)
        self.assertEqual(str(c.exception), 'too_long')
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

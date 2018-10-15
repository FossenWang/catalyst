'测试'

from unittest import TestCase

# from marshmallow import Schema, fields
# from django.forms import fields

from . import Catalyst, StringField, IntegerField, FloatField
from .validators import ValidationError, Validator, LengthValidator, ComparisonValidator, \
    BoolValidator


from pprint import pprint


class TestData:
    def __init__(self, string, integer, _float):
        self.string = string
        self.integer = integer
        self.float = _float


class TestDataCatalyst(Catalyst):
    string = StringField(min_length=2, max_length=12)
    integer = IntegerField(min_value=0, max_value=12, required=True)
    _float = FloatField(name='float', key='float', min_value=-1.1, max_value=1.1)


test_data_catalyst = TestDataCatalyst()
test_data = TestData(string='xxx', integer=1, _float=1.1)


class CatalystTest(TestCase):

    def test_extract(self):
        test_data_dict = test_data_catalyst.extract(test_data)
        self.assertDictEqual(test_data_dict, {'float': 1.1, 'integer': 1, 'string': 'xxx'})

    def test_validate(self):
        # test valid_data
        valid_data = {'string': 'xxx', 'integer': 1, 'float': 1.1}
        result = test_data_catalyst.validate(valid_data)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.invalid_data, {})
        self.assertDictEqual(result.errors, {})
        self.assertDictEqual(result.valid_data, valid_data)

        # test invalid_data: validate errors
        invalid_data = {'string': 'xxx' * 20, 'integer': 100, 'float': 2}
        result = test_data_catalyst.validate(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, invalid_data)
        self.assertEqual(set(result.errors), {'string', 'integer', 'float'})
        self.assertDictEqual(result.valid_data, {})

        # test invalid_data: parse errors
        invalid_data = {'string': 'x', 'integer': 'str', 'float': []}
        result = test_data_catalyst.validate(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, invalid_data)
        self.assertEqual(set(result.errors), {'string', 'integer', 'float'})
        self.assertIsInstance(result.errors['string'], ValidationError)
        self.assertIsInstance(result.errors['integer'], ValueError)
        self.assertIsInstance(result.errors['float'], ValueError)

        # test required field
        # ignore other fields
        invalid_data = valid_data.copy()
        invalid_data.pop('integer')
        result = test_data_catalyst.validate(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, {})
        self.assertEqual(set(result.errors), {'integer'})
        self.assertDictEqual(result.valid_data, invalid_data)

        # test raise error while validating
        raise_err_catalyst = TestDataCatalyst(raise_error=True)
        self.assertRaises(ValidationError, raise_err_catalyst.validate, invalid_data)
        result = raise_err_catalyst.validate(valid_data)
        self.assertTrue(result.is_valid)


class ValidationTest(TestCase):

    def test_vase_validator(self):
        class NewValidator(Validator):
            default_error_messages = {'msg': 'default'}
            def __call__(self, value):
                raise ValidationError(self.error_messages['msg'])

        # test alterable error messages
        default_validator = NewValidator()
        custom_msg_validator = NewValidator(error_messages={'msg': 'custom'})
        try:
            default_validator(0)
        except ValidationError as e:
            self.assertEqual(str(e), 'default')
        try:
            custom_msg_validator(0)
        except ValidationError as e:
            self.assertEqual(str(e), 'custom')
        self.assertDictEqual(NewValidator.default_error_messages, {'msg': 'default'})

    def test_comparison_validator(self):
        compare_integer = ComparisonValidator(0, 100)
        compare_integer(1)
        compare_integer(0)
        compare_integer(100)
        self.assertRaises(ValidationError, compare_integer, -1)
        self.assertRaises(ValidationError, compare_integer, 101)
        self.assertRaises(TypeError, compare_integer, '1')
        self.assertRaises(TypeError, compare_integer, [1])

        compare_integer_float = ComparisonValidator(-1.1, 1.1)

        compare_integer_float(1)
        compare_integer_float(0)
        compare_integer_float(0.1)
        compare_integer_float(1.1)
        compare_integer_float(-1.1)
        self.assertRaises(ValidationError, compare_integer_float, -2)
        self.assertRaises(ValidationError, compare_integer_float, 2)
        self.assertRaises(TypeError, compare_integer_float, '1.1')
        self.assertRaises(TypeError, compare_integer_float, [1.1])

    def test_length_validator(self):
        validator = LengthValidator(2, 10)

        validator('x' * 2)
        validator('x' * 5)
        validator('x' * 10)
        validator(['xzc', 1])
        self.assertRaises(ValidationError, validator, 'x')
        self.assertRaises(ValidationError, validator, 'x' * 11)
        self.assertRaises(ValidationError, validator, '')
        self.assertRaises(TypeError, validator, None)

        validator = LengthValidator(0, 1)
        validator('')
        validator([])

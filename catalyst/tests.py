'测试'

from unittest import TestCase

# from marshmallow import Schema, fields

from . import Catalyst, StringField, IntegerField, FloatField
from .validators import ValidationError, Validator, StringValidator, IntegerValidator, \
    FloatValidator


from pprint import pprint


class TestData:
    def __init__(self, string, integer, _float):
        self.string = string
        self.integer = integer
        self.float = _float


class TestDataCatalyst(Catalyst):
    string = StringField(min_length=0, max_length=12)
    integer = IntegerField(min_value=0, max_value=12, required=True)
    _float = FloatField(name='float', key='float', min_value=-1.1, max_value=1.1)


test_data_catalyst = TestDataCatalyst()
test_data = TestData(string='xxx', integer=1, _float=1.1)


class CatalystTest(TestCase):

    def test_extract(self):
        test_data_dict = test_data_catalyst.extract(test_data)
        self.assertDictEqual(test_data_dict, {'float': 1.1, 'integer': 1, 'string': 'xxx'})

    def test_validate(self):
        valid_data = {'string': 'xxx', 'integer': 1, 'float': 1.1}
        result = test_data_catalyst.validate(valid_data)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.invalid_data, {})
        self.assertDictEqual(result.errors, {})
        self.assertDictEqual(result.valid_data, valid_data)

        invalid_data = {'string': 'xxx' * 20, 'integer': 100, 'float': 2}
        result = test_data_catalyst.validate(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, invalid_data)
        self.assertEqual(set(result.errors), {'string', 'integer', 'float'})
        self.assertDictEqual(result.valid_data, {})

        # test param: required
        # ignore other fields
        invalid_data = valid_data.copy()
        invalid_data.pop('integer')
        result = test_data_catalyst.validate(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, {})
        self.assertEqual(set(result.errors), {'integer'})
        self.assertDictEqual(result.valid_data, invalid_data)

        # pprint((result.errors, result.invalid_data, result.valid_data))


class ValidationTest(TestCase):

    def test_vase_validator(self):
        class NewValidator(Validator):
            default_error_msg = {'msg': 'default'}
            def __call__(self, value):
                raise ValidationError(self.error_msg['msg'])

        # test alterable error messages
        default_validator = NewValidator()
        custom_msg_validator = NewValidator(error_msg={'msg': 'custom'})
        try:
            default_validator(0)
        except ValidationError as e:
            self.assertEqual(str(e), 'default')
        try:
            custom_msg_validator(0)
        except ValidationError as e:
            self.assertEqual(str(e), 'custom')
        self.assertDictEqual(NewValidator.default_error_msg, {'msg': 'default'})

    def test_integer_validator(self):
        validator = IntegerValidator(0, 100)

        self.assertEqual(validator(1), 1)
        self.assertEqual(validator(0), 0)
        self.assertEqual(validator(100), 100)
        self.assertEqual(validator('1'), 1)
        self.assertEqual(validator('0'), 0)
        self.assertEqual(validator('100'), 100)

        self.assertRaises(ValidationError, validator, -1)
        self.assertRaises(ValidationError, validator, 101)
        self.assertRaises(ValidationError, validator, None)
        self.assertRaises(ValidationError, validator, [])

    def test_float_validator(self):
        validator = FloatValidator(-1.1, 1.1)

        self.assertEqual(validator(1), 1.0)
        self.assertEqual(validator(0), 0.0)
        self.assertEqual(validator(0.1), 0.1)
        self.assertEqual(validator(1.1), 1.1)
        self.assertEqual(validator(-1.1), -1.1)
        self.assertEqual(validator('1'), 1.0)

        self.assertRaises(ValidationError, validator, -2)
        self.assertRaises(ValidationError, validator, 2)
        self.assertRaises(ValidationError, validator, None)
        self.assertRaises(ValidationError, validator, [])


    def test_string_validator(self):
        validator = StringValidator(2, 10)

        self.assertEqual(validator('x' * 2), 'x' * 2)
        self.assertEqual(validator('x' * 5), 'x' * 5)
        self.assertEqual(validator('x' * 10), 'x' * 10)
        self.assertEqual(validator(['xzc', 1]), "['xzc', 1]")
        self.assertEqual(validator(None), 'None')

        self.assertRaises(ValidationError, validator, 'x')
        self.assertRaises(ValidationError, validator, 'x' * 11)
        self.assertRaises(ValidationError, validator, '')

        validator = StringValidator(0, 1)
        self.assertEqual(validator(''), '')

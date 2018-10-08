'测试'

from unittest import TestCase

# from marshmallow import Schema, fields

from . import Catalyst, StringField, IntegerField
from .validators import ValidationError, StringValidator, IntegerValidator


from pprint import pprint


class TestData:
    def __init__(self, string, integer):
        self.string = string
        self.integer = integer


class TestDataCatalyst(Catalyst):
    string = StringField(max_length=12, min_length=0)
    integer = IntegerField(max_value=12, min_value=0, required=True)


test_data_catalyst = TestDataCatalyst()
test_data = TestData(string='xxx', integer=1)


class CatalystTest(TestCase):

    def test_extract(self):
        test_data_dict = test_data_catalyst.extract(test_data)
        self.assertDictEqual(test_data_dict, {'integer': 1, 'string': 'xxx'})

    def test_validate(self):
        valid_data = {'string': 'xxx', 'integer': 1}
        result = test_data_catalyst.validate(valid_data)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.invalid_data, {})
        self.assertDictEqual(result.errors, {})
        self.assertDictEqual(result.valid_data, {'integer': 1, 'string': 'xxx'})

        invalid_data = {'string': 'xxx' * 20, 'integer': 100}
        result = test_data_catalyst.validate(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, invalid_data)
        self.assertEqual(set(result.errors), {'string', 'integer'})
        self.assertDictEqual(result.valid_data, {})

        # test param: required
        invalid_data = valid_data.copy()
        invalid_data.pop('integer')
        result = test_data_catalyst.validate(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, {})
        self.assertEqual(set(result.errors), {'integer'})
        self.assertDictEqual(result.valid_data, invalid_data)

        # pprint((result.errors, result.invalid_data, result.valid_data))


class ValidationTest(TestCase):

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

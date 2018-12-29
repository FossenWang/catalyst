from unittest import TestCase

from catalyst import Catalyst
from catalyst.fields import Field, StringField, IntegerField, FloatField, BoolField, ListField, \
    CallableField
from catalyst.validators import ValidationError, Validator, LengthValidator, ComparisonValidator, \
    BoolValidator

# from marshmallow import Schema, fields
# from django.forms import fields
# from pprint import pprint


class TestData:
    def __init__(self, string=None, integer=None, float_=None, bool_=None):
        self.string = string
        self.integer = integer
        self.float_ = float_
        self.bool_ = bool_

    def func(self, a, b, c=1):
        return a + b + c


class TestDataCatalyst(Catalyst):
    string = StringField(min_length=2, max_length=12)
    integer = IntegerField(min_value=0, max_value=12, required=True)
    float_field = FloatField(name='float_', key='float', min_value=-1.1, max_value=1.1)
    bool_field = BoolField(name='bool_', key='bool')
    func = CallableField(name='func', key='func', func_args=(1, 2, 3))


test_data_catalyst = TestDataCatalyst()


class CatalystTest(TestCase):

    def test_dump(self):
        test_data = TestData(string='xxx', integer=1, float_=1.1, bool_=True)
        test_data_dict = test_data_catalyst.dump(test_data)
        self.assertDictEqual(test_data_dict, {
            'float': 1.1, 'integer': 1, 'string': 'xxx',
            'bool': True, 'func': 6,
            })

        catalyst = TestDataCatalyst(fields=[])
        self.assertDictEqual(catalyst._dump_fields, test_data_catalyst._dump_fields)

        catalyst = TestDataCatalyst(fields=['string'])
        self.assertDictEqual(catalyst.dump(test_data), {'string': 'xxx'})

        catalyst = TestDataCatalyst(fields=['string'], dump_fields=['bool_field'])
        self.assertDictEqual(catalyst.dump(test_data), {'bool': True})

        self.assertRaises(KeyError, TestDataCatalyst, fields=['wrong_name'])
        self.assertRaises(KeyError, TestDataCatalyst, dump_fields=['wrong_name'])

    def test_load(self):
        # test valid_data
        valid_data = {'string': 'xxx', 'integer': 1, 'float': 1.1, 'bool': True}
        result = test_data_catalyst.load(valid_data)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.invalid_data, {})
        self.assertDictEqual(result.errors, {})
        self.assertDictEqual(result.valid_data, valid_data)
        self.assertDictEqual(result, valid_data)

        # test invalid_data
        self.assertRaises(TypeError, test_data_catalyst.load, 1)

        # test invalid_data: validate errors
        invalid_data = {'string': 'xxx' * 20, 'integer': 100, 'float': 2}
        result = test_data_catalyst.load(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, invalid_data)
        self.assertEqual(set(result.errors), {'string', 'integer', 'float'})
        self.assertDictEqual(result.valid_data, {})

        # test invalid_data: parse errors
        invalid_data = {'string': 'x', 'integer': 'str', 'float': []}
        result = test_data_catalyst.load(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, invalid_data)
        self.assertEqual(set(result.errors), {'string', 'integer', 'float'})
        self.assertIsInstance(result.errors['string'], ValidationError)
        self.assertIsInstance(result.errors['integer'], ValueError)
        self.assertIsInstance(result.errors['float'], TypeError)

        # test required field
        # ignore other fields
        invalid_data = valid_data.copy()
        invalid_data.pop('integer')
        result = test_data_catalyst.load(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, {})
        self.assertEqual(set(result.errors), {'integer'})
        self.assertDictEqual(result.valid_data, invalid_data)

        # test raise error while validating
        raise_err_catalyst = TestDataCatalyst(raise_error=True)
        self.assertRaises(ValidationError, raise_err_catalyst.load, invalid_data)
        result = raise_err_catalyst.load(valid_data)
        self.assertTrue(result.is_valid)

        # test no load
        catalyst = TestDataCatalyst(fields=[])
        self.assertDictEqual(catalyst._load_fields, test_data_catalyst._load_fields)
        self.assertNotIn('func', catalyst._load_fields.keys())
        catalyst = TestDataCatalyst(fields=['string'])
        self.assertDictEqual(catalyst.load(valid_data).valid_data, {'string': 'xxx'})
        catalyst = TestDataCatalyst(fields=['string'], load_fields=['bool_field'])
        self.assertDictEqual(catalyst.load(valid_data).valid_data, {'bool': True})
        self.assertRaises(KeyError, TestDataCatalyst, load_fields=['wrong_name'])

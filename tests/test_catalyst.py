from unittest import TestCase

from catalyst import Catalyst
from catalyst.fields import StringField, IntegerField, \
    FloatField, BoolField, CallableField
from catalyst.exceptions import ValidationError
from catalyst.utils import dump_from_attribute, dump_from_key


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
        # dump from object
        test_data = TestData(string='xxx', integer=1, float_=1.1, bool_=True)
        dump_result = test_data_catalyst.dump(test_data)
        self.assertDictEqual(dump_result, {
            'float': 1.1, 'integer': 1, 'string': 'xxx',
            'bool': True, 'func': 6,
        })

        catalyst = TestDataCatalyst(fields=[])
        self.assertDictEqual(catalyst._dump_field_dict, test_data_catalyst._dump_field_dict)

        catalyst = TestDataCatalyst(fields=['string'])
        self.assertDictEqual(catalyst.dump(test_data), {'string': 'xxx'})

        catalyst = TestDataCatalyst(fields=['string'], dump_fields=['bool_field'])
        self.assertDictEqual(catalyst.dump(test_data), {'bool': True})

        self.assertRaises(KeyError, TestDataCatalyst, fields=['wrong_name'])
        self.assertRaises(KeyError, TestDataCatalyst, dump_fields=['wrong_name'])

        # dump from dict
        test_data_dict = {
            'float_': 1.1, 'integer': 1, 'string': 'xxx',
            'bool_': True, 'func': test_data.func,
        }
        self.assertEqual(test_data_catalyst.dump(test_data_dict), dump_result)
        self.assertRaises(AttributeError, test_data_catalyst.dump, {'a'})

        # only dump from attribute
        catalyst = TestDataCatalyst(dump_from=dump_from_attribute)
        catalyst.dump(test_data)
        with self.assertRaises(AttributeError):
            catalyst.dump(test_data_dict)

        # only dump from key
        catalyst = TestDataCatalyst(dump_from=dump_from_key)
        catalyst.dump(test_data_dict)
        with self.assertRaises(TypeError):
            catalyst.dump(test_data)

        # wrong args
        with self.assertRaises(TypeError):
            catalyst = TestDataCatalyst(dump_from='wrong')

    def test_load(self):
        # test valid_data
        valid_data = {'string': 'xxx', 'integer': 1, 'float': 1.1, 'bool': True}
        result = test_data_catalyst.load(valid_data)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.invalid_data, {})
        self.assertDictEqual(result.errors, {})
        self.assertDictEqual(result.valid_data, valid_data)
        self.assertDictEqual(result, valid_data)
        # test repr
        self.assertTrue(str(result).startswith('{'))
        self.assertTrue(repr(result).startswith('LoadResult(is_valid=True'))

        # test invalid_data
        self.assertRaises(TypeError, test_data_catalyst.load, 1)

        # test invalid_data: validate errors
        invalid_data = {'string': 'xxx' * 20, 'integer': 100, 'float': 2}
        result = test_data_catalyst.load(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, invalid_data)
        self.assertEqual(set(result.errors), {'string', 'integer', 'float', 'bool'})
        self.assertDictEqual(result.valid_data, {})
        # test repr
        self.assertTrue(str(result).startswith('{'))
        self.assertTrue(repr(result).startswith('LoadResult(is_valid=False'))

        # test invalid_data: parse errors
        invalid_data = {'string': 'x', 'integer': 'str', 'float': []}
        result = test_data_catalyst.load(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, invalid_data)
        self.assertEqual(set(result.errors), {'string', 'integer', 'float', 'bool'})
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
        self.assertDictEqual(catalyst._load_field_dict, test_data_catalyst._load_field_dict)
        self.assertNotIn('func', catalyst._load_field_dict.keys())
        catalyst = TestDataCatalyst(fields=['string'])
        self.assertDictEqual(catalyst.load(valid_data).valid_data, {'string': 'xxx'})
        catalyst = TestDataCatalyst(fields=['string'], load_fields=['bool_field'])
        self.assertDictEqual(catalyst.load(valid_data).valid_data, {'bool': True})
        self.assertRaises(KeyError, TestDataCatalyst, load_fields=['wrong_name'])

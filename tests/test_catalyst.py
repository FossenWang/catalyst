import json
from unittest import TestCase

from catalyst import Catalyst
from catalyst.fields import StringField, IntegerField, \
    FloatField, BoolField, CallableField, ListField
from catalyst.exceptions import ValidationError
from catalyst.utils import dump_from_attribute, dump_from_key


class TestData:
    def __init__(
            self, string=None, integer=None, float_=None,
            bool_=None, list_=None, obj=None):
        self.string = string
        self.integer = integer
        self.float_ = float_
        self.bool_ = bool_
        self.list_ = list_
        self.obj = obj

    def func(self, a, b, c=1):
        return a + b + c


class TestDataCatalyst(Catalyst):
    string = StringField(min_length=2, max_length=12)
    integer = IntegerField(min_value=0, max_value=12, required=True)
    float_field = FloatField(name='float_', key='float', min_value=-1.1, max_value=1.1)
    bool_field = BoolField(name='bool_', key='bool')
    func = CallableField(name='func', key='func', func_args=(1, 2, 3))
    list_ = ListField(StringField())


test_data_catalyst = TestDataCatalyst()


class CatalystTest(TestCase):

    def test_dump(self):
        test_data = TestData(
            string='xxx', integer=1, float_=1.1,
            bool_=True, list_=['a', 'b'])

        # initialize
        catalyst = TestDataCatalyst(fields=[])
        self.assertDictEqual(catalyst._dump_field_dict, test_data_catalyst._dump_field_dict)

        catalyst = TestDataCatalyst(fields=['string'])
        self.assertDictEqual(catalyst.dump(test_data), {'string': 'xxx'})

        catalyst = TestDataCatalyst(fields=['string'], dump_fields=['bool_field'])
        self.assertDictEqual(catalyst.dump(test_data), {'bool': True})

        with self.assertRaises(KeyError):
            TestDataCatalyst(fields=['wrong_name'])
        with self.assertRaises(KeyError):
            TestDataCatalyst(dump_fields=['wrong_name'])

        # dump from object
        dump_result = test_data_catalyst.dump(test_data)
        self.assertDictEqual(dump_result, {
            'bool': True, 'float': 1.1, 'func': 6,
            'integer': 1, 'list_': ['a', 'b'], 'string': 'xxx'})

        # dump to json
        text = test_data_catalyst.dump_to_json(test_data)
        self.assertDictEqual(json.loads(text), dump_result)

        # dump from dict
        test_data_dict = {
            'float_': 1.1, 'integer': 1, 'string': 'xxx',
            'bool_': True, 'func': test_data.func, 'list_': ['a', 'b']
        }
        self.assertEqual(test_data_catalyst.dump(test_data_dict), dump_result)
        with self.assertRaises(AttributeError):
            test_data_catalyst.dump({'a'})

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
        valid_data = {
            'string': 'xxx', 'integer': 1, 'float': 1.1,
            'bool': True, 'list_': ['a', 'b']}
        result = test_data_catalyst.load(valid_data)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.invalid_data, {})
        self.assertDictEqual(result.errors, {})
        self.assertDictEqual(result.valid_data, valid_data)
        self.assertDictEqual(result, valid_data)
        # load from json
        s = json.dumps(valid_data)
        result = test_data_catalyst.load_from_json(s)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.valid_data, valid_data)

        # test repr
        self.assertTrue(str(result).startswith('{'))
        self.assertTrue(repr(result).startswith('LoadResult(is_valid=True'))

        # test invalid_data
        with self.assertRaises(TypeError):
            test_data_catalyst.load(1)

        # test invalid_data: validate errors
        invalid_data = {'string': 'xxx' * 20, 'integer': 100, 'float': 2}
        result = test_data_catalyst.load(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, invalid_data)
        self.assertEqual(set(result.errors), {
            'string', 'integer', 'float', 'bool', 'list_'})
        self.assertDictEqual(result.valid_data, {})
        # load from json
        s = json.dumps(invalid_data)
        result = test_data_catalyst.load_from_json(s)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, invalid_data)

        # test repr
        self.assertTrue(str(result).startswith('{'))
        self.assertTrue(repr(result).startswith('LoadResult(is_valid=False'))

        # test invalid_data: parse errors
        invalid_data = {'string': 'x', 'integer': 'str', 'float': []}
        result = test_data_catalyst.load(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, invalid_data)
        self.assertEqual(set(result.errors), {
            'string', 'integer', 'float', 'bool', 'list_'})
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
        with self.assertRaises(ValidationError):
            test_data_catalyst.load(invalid_data, raise_error=True)

        s = json.dumps(invalid_data)
        with self.assertRaises(ValidationError):
            result = test_data_catalyst.load_from_json(s, raise_error=True)

        raise_err_catalyst = TestDataCatalyst(raise_error=True)
        result = raise_err_catalyst.load(valid_data)
        self.assertTrue(result.is_valid)
        with self.assertRaises(ValidationError):
            raise_err_catalyst.load(invalid_data)

        # test no load
        catalyst = TestDataCatalyst(fields=[])
        self.assertDictEqual(catalyst._load_field_dict, test_data_catalyst._load_field_dict)
        self.assertNotIn('func', catalyst._load_field_dict.keys())
        catalyst = TestDataCatalyst(fields=['string'])
        self.assertDictEqual(catalyst.load(valid_data).valid_data, {'string': 'xxx'})
        catalyst = TestDataCatalyst(fields=['string'], load_fields=['bool_field'])
        self.assertDictEqual(catalyst.load(valid_data).valid_data, {'bool': True})
        with self.assertRaises(KeyError):
            TestDataCatalyst(load_fields=['wrong_name'])

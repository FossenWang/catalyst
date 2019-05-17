import json
from unittest import TestCase

from catalyst import Catalyst
from catalyst.fields import StringField, IntegerField, \
    FloatField, BoolField, CallableField, ListField
from catalyst.exceptions import ValidationError
from catalyst.utils import dump_from_attribute, dump_from_key, missing


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
    string = StringField(min_length=2, max_length=12,
                         dump_default='default', load_default='default')
    integer = IntegerField(min_value=0, max_value=12, load_required=True)
    float_field = FloatField(name='float_', key='float', min_value=-1.1, max_value=1.1)
    bool_field = BoolField(name='bool_', key='bool')
    func = CallableField(name='func', key='func', func_args=(1, 2, 3))
    list_ = ListField(StringField())


test_data_catalyst = TestDataCatalyst()


class CatalystTest(TestCase):

    def setUp(self):
        self.test_data = TestData(
            string='xxx', integer=1, float_=1.1,
            bool_=True, list_=['a', 'b'])

        self.valid_data = {
            'string': 'xxx', 'integer': 1, 'float': 1.1,
            'bool': True, 'list_': ['a', 'b']}

    def test_init(self):
        "Test initializing Catalyst."

        test_data = self.test_data
        valid_data = self.valid_data

        # Empty "fields" has no effect
        catalyst = TestDataCatalyst(fields=[])
        self.assertDictEqual(catalyst._dump_field_dict, test_data_catalyst._dump_field_dict)
        self.assertDictEqual(catalyst._load_field_dict, test_data_catalyst._load_field_dict)
        # if field.no_load is True, this field will be excluded from loading
        self.assertNotIn('func', catalyst._load_field_dict.keys())

        # Specify "fields" for dumping and loading
        catalyst = TestDataCatalyst(fields=['string'])
        self.assertDictEqual(catalyst.dump(test_data), {'string': 'xxx'})
        self.assertDictEqual(catalyst.load(valid_data).valid_data, {'string': 'xxx'})

        # "dump_fields" takes precedence over "fields"
        catalyst = TestDataCatalyst(fields=['string'], dump_fields=['bool_field'])
        self.assertDictEqual(catalyst.dump(test_data), {'bool': True})
        self.assertDictEqual(catalyst.load(valid_data).valid_data, {'string': 'xxx'})

        # "load_fields" takes precedence over "fields"
        catalyst = TestDataCatalyst(fields=['string'], load_fields=['bool_field'])
        self.assertDictEqual(catalyst.dump(test_data), {'string': 'xxx'})
        self.assertDictEqual(catalyst.load(valid_data).valid_data, {'bool': True})

        # When "dump_fields" and "load_fields" are given, fields is not used.
        catalyst = TestDataCatalyst(
            fields=['integer'], dump_fields=['string'], load_fields=['bool_field'])
        self.assertDictEqual(catalyst.dump(test_data), {'string': 'xxx'})
        self.assertDictEqual(catalyst.load(valid_data).valid_data, {'bool': True})

        with self.assertRaises(KeyError):
            TestDataCatalyst(fields=['wrong_name'])

        with self.assertRaises(KeyError):
            TestDataCatalyst(dump_fields=['wrong_name'])

        with self.assertRaises(KeyError):
            TestDataCatalyst(load_fields=['wrong_name'])

    def test_base_dumping(self):
        "Test dumping data."

        test_data = self.test_data

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

        # only get dump value from attribute
        catalyst = TestDataCatalyst(dump_from=dump_from_attribute)
        catalyst.dump(test_data)
        with self.assertRaises(AttributeError):
            catalyst.dump(test_data_dict)

        # only get dump value from key
        catalyst = TestDataCatalyst(dump_from=dump_from_key)
        catalyst.dump(test_data_dict)
        with self.assertRaises(TypeError):
            catalyst.dump(test_data)

        # wrong args
        with self.assertRaises(TypeError):
            catalyst = TestDataCatalyst(dump_from='wrong')

    def test_field_args_which_affect_dumping(self):
        class C(Catalyst):
            s = StringField()

        catalyst = C()

        # default behavior
        # missing field will raise error
        with self.assertRaises(AttributeError):
            catalyst.dump(None)
        with self.assertRaises(KeyError):
            catalyst.dump({})

        # change default field args
        def change_args(
                format_none=False,
                dump_required=True,
                dump_default=missing):
            catalyst.s.format_none = format_none
            catalyst.s.dump_default = dump_default
            catalyst.s.dump_required = dump_required

        # ignore missing field
        change_args(dump_required=False)
        dump_result = catalyst.dump({})
        self.assertEqual(dump_result, {})

        # default value for missing field
        change_args(dump_default='default')
        dump_result = catalyst.dump({})
        self.assertEqual(dump_result['s'], 'default')

        dump_result = catalyst.dump({'s': 1})
        self.assertEqual(dump_result['s'], '1')

        change_args(dump_default=None)
        dump_result = catalyst.dump({})
        self.assertEqual(dump_result['s'], None)

        # pass None to formatter
        change_args(format_none=True)
        dump_result = catalyst.dump({'s': None})
        self.assertEqual(dump_result['s'], 'None')

        change_args(format_none=True, dump_default=None)
        dump_result = catalyst.dump({})
        self.assertEqual(dump_result['s'], 'None')

        # no_dump means ignore this field
        class CC(Catalyst):
            s = StringField(no_dump=True)

        catalyst = CC()

        dump_result = catalyst.dump({})
        self.assertEqual(dump_result, {})

    def test_load(self):
        "Test loading data."

        valid_data = self.valid_data

        # test valid_data
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
            'string', 'integer', 'float'})
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
            'string', 'integer', 'float'})
        self.assertIsInstance(result.errors['string'], ValidationError)
        self.assertIsInstance(result.errors['integer'], ValueError)
        self.assertIsInstance(result.errors['float'], TypeError)

        # raise error while validating
        # set "raise_error" when init
        raise_err_catalyst = TestDataCatalyst(raise_error=True)
        result = raise_err_catalyst.load(valid_data)
        self.assertTrue(result.is_valid)
        with self.assertRaises(ValidationError):
            raise_err_catalyst.load(invalid_data)

        # set "raise_error" when call load
        with self.assertRaises(ValidationError):
            test_data_catalyst.load(invalid_data, raise_error=True)

        # set "raise_error" when call load_from_json
        s = json.dumps(invalid_data)
        with self.assertRaises(ValidationError):
            result = test_data_catalyst.load_from_json(s, raise_error=True)

        # missing field will be excluded
        valid_data_2 = valid_data.copy()
        valid_data_2.pop('float')
        result = test_data_catalyst.load(valid_data_2)
        self.assertTrue(result.is_valid)
        self.assertTrue('float' not in result)

        # default value for missing field
        valid_data_2 = valid_data.copy()
        valid_data_2.pop('string')
        result = test_data_catalyst.load(valid_data_2)
        self.assertTrue(result.is_valid)
        self.assertEqual(result['string'], 'default')

        # raise error when required field is missing
        invalid_data = valid_data.copy()
        invalid_data.pop('integer')
        result = test_data_catalyst.load(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, {})
        self.assertEqual(set(result.errors), {'integer'})
        self.assertDictEqual(result.valid_data, invalid_data)

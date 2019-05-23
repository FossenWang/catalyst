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
    string = StringField(min_length=2, max_length=12,
                         dump_default='default', load_default='default')
    integer = IntegerField(min_value=0, max_value=12, load_required=True)
    float_field = FloatField(name='float_', key='float', min_value=-1.1, max_value=1.1)
    bool_field = BoolField(name='bool_', key='bool')
    func = CallableField(name='func', key='func', func_args=(1, 2, 3))
    list_ = ListField(StringField())


test_data_catalyst = TestDataCatalyst(raise_error=False)


class CatalystTest(TestCase):

    def setUp(self):
        self.test_data = TestData(
            string='xxx', integer=1, float_=1.1,
            bool_=True, list_=['a', 'b'])

        self.valid_data = {
            'string': 'xxx', 'integer': 1, 'float': 1.1,
            'bool': True, 'list_': ['a', 'b']}

    def create_catalyst(self, **kwargs):
        class C(Catalyst):
            s = StringField(**kwargs)
        return C(raise_error=False)

    def assert_field_dump_args(self, data, result=None, **kwargs):
        catalyst = self.create_catalyst(**kwargs)
        self.assertEqual(catalyst.dump(data), result)

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
        result = test_data_catalyst.dump(test_data)
        self.assertDictEqual(result, {
            'bool': True, 'float': 1.1, 'func': 6,
            'integer': 1, 'list_': ['a', 'b'], 'string': 'xxx'})

        # dump to json
        text = test_data_catalyst.dump_to_json(test_data)
        self.assertDictEqual(json.loads(text), result)

        # dump from dict
        test_data_dict = {
            'float_': 1.1, 'integer': 1, 'string': 'xxx',
            'bool_': True, 'func': test_data.func, 'list_': ['a', 'b']
        }
        self.assertEqual(test_data_catalyst.dump(test_data_dict), result)

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
        # default behavior
        # missing field will raise error
        with self.assertRaises(AttributeError):
            self.assert_field_dump_args(None)
        with self.assertRaises(KeyError):
            self.assert_field_dump_args({})

        # ignore missing field
        self.assert_field_dump_args({}, {}, dump_required=False)

        # default value for missing field
        self.assert_field_dump_args(
            {}, {'s': 'default'}, dump_default='default')

        self.assert_field_dump_args(
            {'s': 1}, {'s': '1'}, dump_default='default')

        self.assert_field_dump_args(
            {}, {'s': None}, dump_default=None)

        # callable default
        self.assert_field_dump_args(
            {}, {'s': '1'}, dump_default=lambda: 1)

        # dump_required has no effect if dump_default is set
        with self.assertWarns(Warning):
            self.assert_field_dump_args(
                {}, {'s': None}, dump_required=True, dump_default=None)

        # pass None to formatter
        self.assert_field_dump_args(
            {'s': None}, {'s': 'None'}, format_none=True)

        self.assert_field_dump_args(
            {}, {'s': 'None'}, format_none=True, dump_default=None)

        # no_dump means ignore this field
        self.assert_field_dump_args({1: 1}, {}, no_dump=True)

    def test_base_loading(self):
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

    def test_field_args_which_affect_loading(self):

        # default behavior
        # missing field will be excluded
        catalyst = self.create_catalyst()
        result = catalyst.load({})
        self.assertTrue(result.is_valid)
        self.assertTrue(result.valid_data == {})

        # default value for missing field
        catalyst = self.create_catalyst(load_default=None)
        result = catalyst.load({})
        self.assertTrue(result.is_valid)
        self.assertEqual(result['s'], None)

        result = catalyst.load({'s': 1})
        self.assertTrue(result.is_valid)
        self.assertEqual(result['s'], '1')

        catalyst = self.create_catalyst(load_default=1)
        result = catalyst.load({})
        self.assertTrue(result.is_valid)
        self.assertEqual(result['s'], '1')

        # callable default
        catalyst = self.create_catalyst(load_default=lambda: 1)
        result = catalyst.load({})
        self.assertTrue(result.is_valid)
        self.assertEqual(result['s'], '1')

        # invalid when required field is missing
        catalyst = self.create_catalyst(load_required=True)
        result = catalyst.load({})
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.valid_data, {})
        self.assertDictEqual(result.invalid_data, {})
        self.assertEqual(set(result.errors), {'s'})

        # load_required has no effect if load_default is set
        with self.assertWarns(Warning):
            catalyst = self.create_catalyst(load_required=True, load_default=None)
        result = catalyst.load({})
        self.assertTrue(result.is_valid)
        self.assertEqual(result['s'], None)

        # pass None to parser and validators
        catalyst = self.create_catalyst(parse_none=True)
        result = catalyst.load({'s': None})
        self.assertTrue(result.is_valid)
        self.assertEqual(result['s'], 'None')

        catalyst = self.create_catalyst(parse_none=True, load_default=None)
        result = catalyst.load({})
        self.assertTrue(result.is_valid)
        self.assertEqual(result['s'], 'None')

        # parse_none has no effect if allow_none is False
        with self.assertWarns(Warning):
            catalyst = self.create_catalyst(parse_none=True, allow_none=False)
        result = catalyst.load({'s': None})
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.valid_data, {})
        self.assertDictEqual(result.invalid_data, {'s': None})
        self.assertEqual(set(result.errors), {'s'})

        # always invalid if load_default is None and allow_none is False
        catalyst = self.create_catalyst(allow_none=False, load_default=None)
        result = catalyst.load({})
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.valid_data, {})
        self.assertDictEqual(result.invalid_data, {'s': None})
        self.assertEqual(set(result.errors), {'s'})

        # no_load means ignore this field
        class CC(Catalyst):
            s = StringField(no_load=True)

        catalyst = CC()

        result = catalyst.load({})
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.valid_data, {})

'测试'

from unittest import TestCase

from marshmallow import Schema, fields
# from django.forms import fields

from . import Catalyst
from .fields import Field, StringField, IntegerField, FloatField, BoolField, ListField, \
    CallableField
from .validators import ValidationError, Validator, LengthValidator, ComparisonValidator, \
    BoolValidator


from pprint import pprint


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


class FieldTest(TestCase):
    def test_field(self):
        class A(Catalyst):
            fixed_value = Field()
            key_1 = Field()
            key_2 = Field()

            @staticmethod
            @key_1.set_dump_from
            @key_2.set_dump_from
            def from_dict_key(obj, name):
                return obj[name]

            @staticmethod
            @fixed_value.set_formatter
            def fixed_value_formatter(value):
                return 1

            @fixed_value.set_parse
            def parse_fixed_value(value):
                return value + 1

            @fixed_value.set_validator
            def validate_fixed_value(value):
                return value + 1  # 返回值无用

            @fixed_value.set_after_validate
            def after_validate_fixed_value(value):
                return value + 1

        # test formatter
        field_1 = Field(formatter=A.fixed_value_formatter)
        self.assertEqual(field_1.formatter, A.fixed_value_formatter)
        a = A()
        test_data = TestData()
        test_data.fixed_value = 'asd'
        self.assertEqual(a.fixed_value.dump(test_data), 1)
        test_data.fixed_value = 1000
        self.assertEqual(a.fixed_value.dump(test_data), 1)
        test_data.fixed_value = [100]
        self.assertEqual(a.fixed_value.dump(test_data), 1)

        # test dump_from
        field_2 = Field(dump_from=A.from_dict_key)
        self.assertEqual(field_2.dump_from, A.from_dict_key)
        self.assertEqual(a.key_1.dump({'key_1': 1,}), 1)
        self.assertEqual(a.key_2.dump({'key_2': 2,}), 2)
        test_data.key = 1
        self.assertRaises(TypeError, a.key_1.dump, test_data)

        # test after validate
        self.assertEqual(a.fixed_value.load({'fixed_value': 0}), 2)
        self.assertRaises(TypeError, a.fixed_value.load, {'fixed_value': '0'})

        # test error msg
        field_3 = Field(key='a', allow_none=False, error_messages={'allow_none': '666'})
        try:
            field_3.load({'a': None})
        except ValidationError as e:
            self.assertEqual(e.args[0], '666')

    def test_string_field(self):
        string_field = StringField(name='string', key='string', min_length=2, max_length=12)

        # dump
        test_data = TestData(string='xxx')
        self.assertEqual(string_field.dump(test_data), 'xxx')
        test_data.string = 1
        self.assertEqual(string_field.dump(test_data), '1')
        test_data.string = []
        self.assertEqual(string_field.dump(test_data), '[]')
        test_data.string = None
        self.assertEqual(string_field.dump(test_data), None)

        # load
        self.assertEqual(string_field.load({'string': 'xxx'}), 'xxx')
        self.assertEqual(string_field.load({'string': 123}), '123')
        self.assertEqual(string_field.load({'string': [1]}), '[1]')
        self.assertEqual(string_field.load({'string': None}), None)
        self.assertEqual(string_field.load({}), None)
        self.assertRaises(ValidationError, string_field.load, {'string': ''})

        string_field.allow_none = False
        self.assertRaises(ValidationError, string_field.load, {'string': None})

        string_field.required = True
        self.assertRaises(ValidationError, string_field.load, {})

    def test_int_field(self):
        int_field = IntegerField(name='integer', key='integer', min_value=-10, max_value=100)

        # dump
        test_data = TestData(integer=1)
        self.assertEqual(int_field.dump(test_data), 1)
        test_data.integer = 1.6
        self.assertEqual(int_field.dump(test_data), 1)
        test_data.integer = '10'
        self.assertEqual(int_field.dump(test_data), 10)

        # load
        self.assertEqual(int_field.load({'integer': 0}), 0)
        self.assertEqual(int_field.load({'integer': 1}), 1)
        self.assertEqual(int_field.load({'integer': '1'}), 1)
        self.assertEqual(int_field.load({'integer': None}), None)
        self.assertEqual(int_field.load({}), None)

        self.assertRaises(ValueError, int_field.load, {'integer': ''})
        self.assertRaises(ValidationError, int_field.load, {'integer': 111})
        self.assertRaises(ValueError, int_field.load, {'integer': 'asd'})
        self.assertRaises(TypeError, int_field.load, {'integer': []})

    def test_float_field(self):
        float_field = FloatField(name='float_', key='float', min_value=-11.1, max_value=111.1)

        # dump
        test_data = TestData(float_=1)
        self.assertEqual(float_field.dump(test_data), 1.0)
        test_data.float_ = 0
        self.assertEqual(float_field.dump(test_data), 0.0)
        test_data.float_ = 5.5
        self.assertEqual(float_field.dump(test_data), 5.5)
        test_data.float_ = '10'
        self.assertEqual(float_field.dump(test_data), 10.0)
        test_data.float_ = None
        self.assertEqual(float_field.dump(test_data), None)

        # load
        self.assertEqual(float_field.load({'float': 0}), 0.0)
        self.assertEqual(float_field.load({'float': '1.1'}), 1.1)
        self.assertEqual(float_field.load({'float': -11.1}), -11.1)
        self.assertEqual(float_field.load({'float': 111.1}), 111.1)
        self.assertEqual(float_field.load({'float': 11}), 11)
        self.assertEqual(float_field.load({'float': None}), None)
        self.assertEqual(float_field.load({}), None)

        self.assertRaises(ValueError, float_field.load, {'float': ''})
        self.assertRaises(ValidationError, float_field.load, {'float': 111.11})
        self.assertRaises(TypeError, float_field.load, {'float': []})

    def test_bool_field(self):
        bool_field = BoolField(name='bool_', key='bool')

        # dump
        test_data = TestData(bool_=True)
        self.assertEqual(bool_field.dump(test_data), True)
        test_data.bool_ = False
        self.assertEqual(bool_field.dump(test_data), False)
        test_data.bool_ = None
        self.assertEqual(bool_field.dump(test_data), None)

        # load
        self.assertEqual(bool_field.load({'bool': True}), True)
        self.assertEqual(bool_field.load({'bool': False}), False)
        self.assertEqual(bool_field.load({'bool': 'False'}), True)
        self.assertEqual(bool_field.load({'bool': 0}), False)
        self.assertEqual(bool_field.load({'bool': 1}), True)
        self.assertEqual(bool_field.load({'bool': []}), False)

    def test_list_field(self):
        list_field = ListField(name='list_', key='list', item_field=FloatField())

        # dump
        test_data = TestData()
        test_data.list_ = [1, 2, 3]
        self.assertListEqual(list_field.dump(test_data), [1.0, 2.0, 3.0])
        test_data.list_ = []
        self.assertListEqual(list_field.dump(test_data), [])
        test_data.list_ = None
        self.assertEqual(list_field.dump(test_data), None)

        # load
        self.assertListEqual(list_field.load({'list': [1, 2, 3]}), [1.0, 2.0, 3.0])
        self.assertListEqual(list_field.load({'list': []}), [])
        self.assertEqual(list_field.load({'list':None}), None)

    def test_callable_field(self):
        callable_field = CallableField(name='func', func_args=[1, 2], func_kwargs={'c': 3})
        # dump
        test_data = TestData()
        self.assertEqual(callable_field.dump(test_data), 6)



class ValidationTest(TestCase):

    def test_base_validator(self):
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

    def test_bool_validator(self):
        validator = BoolValidator()

        validator(True)
        validator(False)
        self.assertRaises(ValidationError, validator, '')
        self.assertRaises(ValidationError, validator, 1)
        self.assertRaises(ValidationError, validator, None)
        self.assertRaises(ValidationError, validator, [])

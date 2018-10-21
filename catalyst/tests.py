'测试'

from unittest import TestCase

from marshmallow import Schema, fields
# from django.forms import fields

from . import Catalyst
from .fields import Field, StringField, IntegerField, FloatField, BoolField, ListField
from .validators import ValidationError, Validator, LengthValidator, ComparisonValidator, \
    BoolValidator


from pprint import pprint


class TestData:
    def __init__(self, string=None, integer=None, float_=None, bool_=None):
        self.string = string
        self.integer = integer
        self.float_ = float_
        self.bool_ = bool_


class TestDataCatalyst(Catalyst):
    string = StringField(min_length=2, max_length=12)
    integer = IntegerField(min_value=0, max_value=12, required=True)
    float_field = FloatField(name='float_', key='float', min_value=-1.1, max_value=1.1)
    bool_field = BoolField(name='bool_', key='bool')


test_data_catalyst = TestDataCatalyst()


class CatalystTest(TestCase):

    def test_serialize(self):
        test_data = TestData(string='xxx', integer=1, float_=1.1, bool_=True)
        test_data_dict = test_data_catalyst.serialize(test_data)
        self.assertDictEqual(test_data_dict, {
            'float': 1.1, 'integer': 1, 'string': 'xxx',
            'bool': True,
            })

    def test_deserialize(self):
        # test valid_data
        valid_data = {'string': 'xxx', 'integer': 1, 'float': 1.1, 'bool': True}
        result = test_data_catalyst.deserialize(valid_data)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.invalid_data, {})
        self.assertDictEqual(result.errors, {})
        self.assertDictEqual(result.valid_data, valid_data)

        # test invalid_data: validate errors
        invalid_data = {'string': 'xxx' * 20, 'integer': 100, 'float': 2}
        result = test_data_catalyst.deserialize(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, invalid_data)
        self.assertEqual(set(result.errors), {'string', 'integer', 'float'})
        self.assertDictEqual(result.valid_data, {})

        # test invalid_data: parse errors
        invalid_data = {'string': 'x', 'integer': 'str', 'float': []}
        result = test_data_catalyst.deserialize(invalid_data)
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
        result = test_data_catalyst.deserialize(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, {})
        self.assertEqual(set(result.errors), {'integer'})
        self.assertDictEqual(result.valid_data, invalid_data)

        # test raise error while validating
        raise_err_catalyst = TestDataCatalyst(raise_error=True)
        self.assertRaises(ValidationError, raise_err_catalyst.deserialize, invalid_data)
        result = raise_err_catalyst.deserialize(valid_data)
        self.assertTrue(result.is_valid)


class FieldTest(TestCase):
    def test_field(self):
        class A(Catalyst):
            fixed_value = Field()
            key_1 = Field()
            key_2 = Field()

            @staticmethod
            @key_1.set_source
            @key_2.set_source
            def from_dict_key(obj, name):
                return obj[name]

            @staticmethod
            @fixed_value.set_formatter
            def fixed_value_formatter(value):
                return 1

            @fixed_value.set_before_validate
            def before_validate_fixed_value(value):
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
        self.assertEqual(a.fixed_value.serialize(test_data), 1)
        test_data.fixed_value = 1000
        self.assertEqual(a.fixed_value.serialize(test_data), 1)
        test_data.fixed_value = [100]
        self.assertEqual(a.fixed_value.serialize(test_data), 1)

        # test source
        field_2 = Field(source=A.from_dict_key)
        self.assertEqual(field_2.source, A.from_dict_key)
        self.assertEqual(a.key_1.serialize({'key_1': 1,}), 1)
        self.assertEqual(a.key_2.serialize({'key_2': 2,}), 2)
        test_data.key = 1
        self.assertRaises(TypeError, a.key_1.serialize, test_data)

        # test after validate
        self.assertEqual(a.fixed_value.deserialize({'fixed_value': 0}), 2)
        self.assertRaises(TypeError, a.fixed_value.deserialize, {'fixed_value': '0'})

        # test error msg
        field_3 = Field(key='a', allow_none=False, error_messages={'allow_none': '666'})
        try:
            field_3.deserialize({'a': None})
        except ValidationError as e:
            self.assertEqual(e.args[0], '666')

    def test_string_field(self):
        string_field = StringField(name='string', key='string', min_length=2, max_length=12)

        # serialize
        test_data = TestData(string='xxx')
        self.assertEqual(string_field.serialize(test_data), 'xxx')
        test_data.string = 1
        self.assertEqual(string_field.serialize(test_data), '1')
        test_data.string = []
        self.assertEqual(string_field.serialize(test_data), '[]')
        test_data.string = None
        self.assertEqual(string_field.serialize(test_data), None)

        # deserialize
        self.assertEqual(string_field.deserialize({'string': 'xxx'}), 'xxx')
        self.assertEqual(string_field.deserialize({'string': 123}), '123')
        self.assertEqual(string_field.deserialize({'string': [1]}), '[1]')
        self.assertEqual(string_field.deserialize({'string': None}), None)
        self.assertEqual(string_field.deserialize({}), None)
        self.assertRaises(ValidationError, string_field.deserialize, {'string': ''})

        string_field.allow_none = False
        self.assertRaises(ValidationError, string_field.deserialize, {'string': None})

        string_field.required = True
        self.assertRaises(ValidationError, string_field.deserialize, {})

    def test_int_field(self):
        int_field = IntegerField(name='integer', key='integer', min_value=-10, max_value=100)

        # serialize
        test_data = TestData(integer=1)
        self.assertEqual(int_field.serialize(test_data), 1)
        test_data.integer = 1.6
        self.assertEqual(int_field.serialize(test_data), 1)
        test_data.integer = '10'
        self.assertEqual(int_field.serialize(test_data), 10)

        # deserialize
        self.assertEqual(int_field.deserialize({'integer': 0}), 0)
        self.assertEqual(int_field.deserialize({'integer': 1}), 1)
        self.assertEqual(int_field.deserialize({'integer': '1'}), 1)
        self.assertEqual(int_field.deserialize({'integer': None}), None)
        self.assertEqual(int_field.deserialize({}), None)

        self.assertRaises(ValueError, int_field.deserialize, {'integer': ''})
        self.assertRaises(ValidationError, int_field.deserialize, {'integer': 111})
        self.assertRaises(ValueError, int_field.deserialize, {'integer': 'asd'})
        self.assertRaises(TypeError, int_field.deserialize, {'integer': []})

    def test_float_field(self):
        float_field = FloatField(name='float_', key='float', min_value=-11.1, max_value=111.1)

        # serialize
        test_data = TestData(float_=1)
        self.assertEqual(float_field.serialize(test_data), 1.0)
        test_data.float_ = 0
        self.assertEqual(float_field.serialize(test_data), 0.0)
        test_data.float_ = 5.5
        self.assertEqual(float_field.serialize(test_data), 5.5)
        test_data.float_ = '10'
        self.assertEqual(float_field.serialize(test_data), 10.0)
        test_data.float_ = None
        self.assertEqual(float_field.serialize(test_data), None)

        # deserialize
        self.assertEqual(float_field.deserialize({'float': 0}), 0.0)
        self.assertEqual(float_field.deserialize({'float': '1.1'}), 1.1)
        self.assertEqual(float_field.deserialize({'float': -11.1}), -11.1)
        self.assertEqual(float_field.deserialize({'float': 111.1}), 111.1)
        self.assertEqual(float_field.deserialize({'float': 11}), 11)
        self.assertEqual(float_field.deserialize({'float': None}), None)
        self.assertEqual(float_field.deserialize({}), None)

        self.assertRaises(ValueError, float_field.deserialize, {'float': ''})
        self.assertRaises(ValidationError, float_field.deserialize, {'float': 111.11})
        self.assertRaises(TypeError, float_field.deserialize, {'float': []})

        # class TestSchema(Schema):
        #     string = fields.String(allow_none=True, required=True)
        # ts = TestSchema()
        # pprint(ts.load({'string': None}))

    def test_bool_field(self):
        bool_field = BoolField(name='bool_', key='bool')

        # serialize
        test_data = TestData(bool_=True)
        self.assertEqual(bool_field.serialize(test_data), True)
        test_data.bool_ = False
        self.assertEqual(bool_field.serialize(test_data), False)
        test_data.bool_ = None
        self.assertEqual(bool_field.serialize(test_data), None)

        # deserialize
        self.assertEqual(bool_field.deserialize({'bool': True}), True)
        self.assertEqual(bool_field.deserialize({'bool': False}), False)
        self.assertEqual(bool_field.deserialize({'bool': 'False'}), True)
        self.assertEqual(bool_field.deserialize({'bool': 0}), False)
        self.assertEqual(bool_field.deserialize({'bool': 1}), True)
        self.assertEqual(bool_field.deserialize({'bool': []}), False)

    def test_list_field(self):
        list_field = ListField(name='list_', key='list', item_field=FloatField())

        # serialize
        test_data = TestData()
        test_data.list_ = [1, 2, 3]
        self.assertListEqual(list_field.serialize(test_data), [1.0, 2.0, 3.0])

        # deserialize
        self.assertListEqual(list_field.deserialize({'list': [1, 2, 3]}), [1.0, 2.0, 3.0])


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

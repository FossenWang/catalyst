'测试'

from unittest import TestCase

from marshmallow import Schema, fields
# from django.forms import fields

from . import Catalyst, StringField, IntegerField, FloatField, BoolField
from .validators import ValidationError, Validator, LengthValidator, ComparisonValidator, \
    BoolValidator


from pprint import pprint


class TestData:
    def __init__(self, string=None, integer=None, float_=None, bool_=None):
        self.string = string
        self.integer = integer
        self.float = float_
        self.bool = bool_


class TestDataCatalyst(Catalyst):
    string = StringField(min_length=2, max_length=12)
    integer = IntegerField(min_value=0, max_value=12, required=True)
    float_field = FloatField(name='float', key='float', min_value=-1.1, max_value=1.1)
    bool_field = BoolField(name='bool', key='bool')


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
        self.assertIsInstance(result.errors['integer'], ValidationError)
        self.assertIsInstance(result.errors['float'], ValidationError)

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
    def test_string_field(self):
        test_data = TestData(string='xxx')
        string_field = StringField(name='string', key='string', min_length=2, max_length=12)
        # serialize
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
        test_data = TestData(integer=1)
        int_field = IntegerField(name='integer', key='integer', min_value=-10, max_value=100)
        # serialize
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

        self.assertRaises(ValidationError, int_field.deserialize, {'integer': ''})
        self.assertRaises(ValidationError, int_field.deserialize, {'integer': 111})
        self.assertRaises(ValidationError, int_field.deserialize, {'integer': 'asd'})
        self.assertRaises(ValidationError, int_field.deserialize, {'integer': []})

        # class TestSchema(Schema):
        #     string = fields.String(allow_none=True, required=True)
        # ts = TestSchema()
        # pprint(ts.load({'string': None}))


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

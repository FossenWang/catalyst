'测试'

from unittest import TestCase

from marshmallow import Schema, fields

from . import Catalyst, StringField, IntegerField

from pprint import pprint


class TestData:
    def __init__(self, string, integer):
        self.string = string
        self.integer = integer
        


class TestDataCatalyst(Catalyst):
    string = StringField(max_length=12, min_length=0)
    integer = IntegerField(max_value=12, min_value=0, required=True)


class CatalystTest(TestCase):
    def test(self):
        test_data_catalyst = TestDataCatalyst()
        test_data = TestData(string='xxx', integer=1)

        test_data_dict = test_data_catalyst.extract(test_data)
        self.assertDictEqual(test_data_dict, {'integer': 1, 'string': 'xxx'})

        result = test_data_catalyst.validate(test_data_dict)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.invalid_data, {})
        self.assertDictEqual(result.errors, {})
        self.assertDictEqual(result.valid_data, {'integer': 1, 'string': 'xxx'})

        invalid_data = {'string': 'xxx' * 20, 'integer': 100,}
        result = test_data_catalyst.validate(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, invalid_data)
        self.assertEqual(set(result.errors), {'string', 'integer'})
        self.assertDictEqual(result.valid_data, {})

        # pprint((result.errors, result.invalid_data, result.valid_data))

# TestData -> 
# {
#     'string': 'xxx',
#     'content': 'xxxxxx',
# }

from unittest import TestCase

from catalyst.core import Catalyst
from catalyst.fields import IntegerField
from catalyst.groups import FieldGroup, ComparisonFieldGroup
from catalyst.exceptions import ValidationError


class GroupsTest(TestCase):
    def test_field_group(self):
        group = FieldGroup(declared_fields=['num'])

        self.assertFalse(hasattr(group, 'fields'))

        fields = {'num': IntegerField(), 'xxx': IntegerField()}
        group.set_fields(fields)
        self.assertEqual(set(group.fields), {'num'})

        with self.assertRaises(TypeError):
            group.set_fields({'num': None})

        self.assertIsNone(group.load(None))
        self.assertIsNone(group.dump(None))

        @group.set_dump
        @group.set_load
        def test_override(data):
            data['xxx'] = 1
            return data

        self.assertEqual(test_override, group.dump)
        self.assertEqual(test_override, group.load)
        self.assertEqual(group.dump({})['xxx'], 1)
        self.assertEqual(group.load({})['xxx'], 1)

    def test_comparison_field_group(self):
        class ComparisonCatalyst(Catalyst):
            lower_limit = IntegerField()
            upper_limit = IntegerField()
            comparison = ComparisonFieldGroup('upper_limit', '>', 'lower_limit')

        catalyst = ComparisonCatalyst()
        self.assertEqual({'lower_limit', 'upper_limit'}, set(catalyst.comparison.fields))
        self.assertEqual({'lower_limit', 'upper_limit'}, set(catalyst._dump_fields))
        self.assertEqual({'lower_limit', 'upper_limit', 'comparison'}, set(catalyst._load_fields))

        valid_data = {'upper_limit': 100, 'lower_limit': 1}
        result = catalyst.load(valid_data)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(valid_data, result.valid_data)

        invalid_data = {'upper_limit': 1, 'lower_limit': 100}
        result = catalyst.load(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertIn('comparison', result.errors)
        self.assertDictEqual(invalid_data, result.invalid_data)

        ignored_data = {'upper_limit': 100, 'lower_limit': None}
        result = catalyst.load(ignored_data)
        self.assertTrue(result.is_valid)

        ignored_data = {'upper_limit': None, 'lower_limit': None}
        result = catalyst.load(ignored_data)
        self.assertTrue(result.is_valid)

        # test dump
        result = catalyst.dump(valid_data)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(valid_data, result.valid_data)

        result = catalyst.comparison.dump(valid_data)
        self.assertDictEqual(valid_data, result)

        result = catalyst.dump(invalid_data)
        self.assertTrue(result.is_valid)

        with self.assertRaises(ValidationError):
            catalyst.comparison.dump(invalid_data)

        with self.assertRaises(ValueError):
            ComparisonFieldGroup('', 'xxx', '')

        with self.assertRaises(ValueError):
            catalyst.comparison.set_fields({})

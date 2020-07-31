from unittest import TestCase

from catalyst.core import Catalyst
from catalyst.fields import NestedField, IntegerField, DecimalField, StringField
from catalyst.groups import FieldGroup, CompareFields, TransformNested, SumFields
from catalyst.exceptions import ValidationError


class GroupsTest(TestCase):
    def test_field_group(self):
        group = FieldGroup(declared_fields=['num'])

        self.assertFalse(hasattr(group, 'fields'))

        fields = {'num': IntegerField(), 'xxx': IntegerField()}
        group.set_fields(fields)
        self.assertEqual(set(group.fields), {'num'})

        with self.assertRaises(ValueError):
            group.set_fields({})

        with self.assertRaises(TypeError):
            group.set_fields({'num': None})

        self.assertIsNone(group.load(None))
        self.assertIsNone(group.dump(None))

        # test "*" all fields, exclude FieldGroup
        group = FieldGroup(declared_fields='*')
        fields['group'] = group
        group.set_fields(fields)
        self.assertSetEqual(set(group.fields), {'xxx', 'num'})

        # test override method
        @group.set_dump
        @group.set_load
        def test_override(data):
            data['xxx'] = 1
            return data

        self.assertEqual(test_override, group.dump)
        self.assertEqual(test_override, group.load)
        self.assertEqual(group.dump({})['xxx'], 1)
        self.assertEqual(group.load({})['xxx'], 1)

        @group.set_dump
        def self_and_group(self, data, group):
            assert self is group
            assert isinstance(self, FieldGroup)
            data['xxx'] = 1
            return data
        self.assertEqual(group.dump, self_and_group)
        self.assertEqual(group.dump({})['xxx'], 1)

    def test_compare_fields(self):
        class ComparisonCatalyst(Catalyst):
            lower_limit = IntegerField()
            upper_limit = IntegerField()
            comparison = CompareFields('upper_limit', '>', 'lower_limit')

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
            CompareFields('', 'xxx', '')

        with self.assertRaises(ValueError):
            catalyst.comparison.set_fields({})

    def test_transform_nested(self):
        coordinate_catalyst = Catalyst({'x': IntegerField(), 'y': IntegerField()})
        class TransformCatalyst(Catalyst):
            a = IntegerField()
            coordinate = NestedField(coordinate_catalyst)
            transform = TransformNested('coordinate')

        catalyst = TransformCatalyst()

        # test wrong fields
        with self.assertRaises(ValueError):
            catalyst.transform.set_fields(fields={})

        with self.assertRaises(TypeError) as cm:
            catalyst.transform.set_fields(fields={'coordinate': IntegerField()})
        self.assertIn('NestedField', str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            catalyst.transform.set_fields(fields={
                'coordinate': NestedField(coordinate_catalyst, many=True)})
        self.assertIn('many=True', str(cm.exception))

        # test valid
        loading_data = {'a': 0, 'x': 1, 'y': -1}
        dumping_data = {'a': 0, 'coordinate': {'x': 1, 'y': -1}}

        result = catalyst.load(loading_data)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.valid_data, dumping_data)

        result = catalyst.dump(dumping_data)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.valid_data, loading_data)

        # test invalid
        invalid_loading_data = {'a': 0, 'x': 'x', 'y': -1}
        result = catalyst.load(invalid_loading_data)
        self.assertFalse(result.is_valid)
        self.assertSetEqual(set(result.errors), {'x'})
        self.assertDictEqual(result.invalid_data, {'x': 'x'})

        invalid_dumping_data = {'a': 0, 'coordinate': {'x': 'x', 'y': -1}}
        result = catalyst.dump(invalid_dumping_data)
        self.assertFalse(result.is_valid)
        self.assertSetEqual(set(result.errors), {'coordinate'})
        self.assertDictEqual(result.invalid_data, {'coordinate': {'x': 'x'}})

        # test change process methods
        fields = {'x': catalyst.coordinate}

        with self.assertRaises(AttributeError):
            TransformNested('x', dump_method='wrong').set_fields(fields)
        with self.assertRaises(AttributeError):
            TransformNested('x', load_method='wrong').set_fields(fields)

        class ReversedTransformCatalyst(TransformCatalyst):
            coordinate = NestedField(coordinate_catalyst, dump_required=False)
            transform = TransformNested(
                'coordinate', dump_method='flat_to_nested', load_method='nested_to_flat')

        reversed_catalyst = ReversedTransformCatalyst()

        dumping_data = {'a': 0, 'x': 1, 'y': -1}
        loading_data = {'a': 0, 'coordinate': {'x': 1, 'y': -1}}

        result = reversed_catalyst.dump(dumping_data)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.valid_data, loading_data)

        result = reversed_catalyst.load(loading_data)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.valid_data, dumping_data)

    def test_sum_fields(self):
        decimal_field = DecimalField()

        class SumCatalyst(Catalyst):
            a = IntegerField()
            b = IntegerField()
            total = SumFields(decimal_field, declared_fields='*')

        catalyst = SumCatalyst()
        self.assertSetEqual(set(catalyst.total.fields), {'a', 'b'})

        data = {'a': 1, 'b': 2}

        result = catalyst.dump(data)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.valid_data['total'], '3')

        result = catalyst.load(data)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.valid_data['total'], decimal_field.to_decimal(3))

        # wrong type
        with self.assertRaises(TypeError):
            SumFields('xxx')

        with self.assertRaises(TypeError):
            SumCatalyst.total.set_fields({'x': StringField()})

from unittest import TestCase


from catalyst.core import Catalyst
from catalyst.packer import CatalystPacker
from catalyst.fields import FloatField
from catalyst.exceptions import ValidationError


class PackerTest(TestCase):
    def test_packer(self):
        # test init packer
        packer = CatalystPacker(raise_error=True, all_errors=False)
        self.assertTrue(packer.raise_error)
        self.assertFalse(packer.all_errors)

        class A(Catalyst):
            a = FloatField()

        class B(Catalyst):
            b = FloatField()

        class C(Catalyst):
            c = FloatField()

        a, b, c = A(), B(), C()
        packer = CatalystPacker((a, b, c))
        packer_2 = CatalystPacker((a, b, c), all_errors=False)

        valid_data = ({'a': 0.0}, {'b': 1.0}, {'c': 2.0})
        valid_result = {'a': 0.0, 'b': 1.0, 'c': 2.0}

        result = packer.dump(valid_data)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.valid_data, valid_result)

        result = packer.load(valid_data)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.valid_data, valid_result)

        invalid_data = ({'a': 'a'}, {'b': 'b'}, {'c': 'c'})

        result = packer.dump(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertEqual(set(result.errors), {'b', 'c', 'a'})

        result = packer_2.dump(invalid_data)
        self.assertEqual(set(result.errors), {'a'})

        with self.assertRaises(ValidationError) as ctx:
            packer.dump(invalid_data, raise_error=True)
        result = ctx.exception.msg
        self.assertFalse(result.is_valid)
        self.assertEqual(set(result.errors), {'b', 'c', 'a'})

        result = packer.load(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertEqual(set(result.errors), {'a', 'b', 'c'})

        with self.assertRaises(ValueError):
            packer._make_processor('xxx', False)

        # process many
        valid_data = [
            [{'a': 0.0}, {'a': 1.0}, {'a': 2.0}],
            [{'b': 0.0}, {'b': 1.0}, {'b': 2.0}],
            [{'c': 0.0}, {'c': 1.0}, {'c': 2.0}],
        ]
        valid_result = [
            {'a': 0.0, 'b': 0.0, 'c': 0.0},
            {'a': 1.0, 'b': 1.0, 'c': 1.0},
            {'a': 2.0, 'b': 2.0, 'c': 2.0}
        ]

        result = packer.dump_many(valid_data)
        self.assertTrue(result.is_valid)
        self.assertListEqual(result.valid_data, valid_result)

        result = packer.load_many(valid_data)
        self.assertTrue(result.is_valid)
        self.assertListEqual(result.valid_data, valid_result)

        invalid_data = [
            [{'a': 0.0}, {'a': 1.0}, {'a': 2.0}],
            [{'b': 0.0}, {'b': 'b'}, {'b': 2.0}],
            [{'c': 'c'}, {'c': 1.0}, {'c': 2.0}],
        ]

        result = packer.load_many(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, {0: {'c': 'c'}, 1: {'b': 'b'}})
        self.assertListEqual(result.valid_data, [
            {'a': 0.0, 'b': 0.0},
            {'a': 1.0, 'c': 1.0},
            {'a': 2.0, 'b': 2.0, 'c': 2.0}
        ])

        result = packer_2.load_many(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, {0: {'c': 'c'}})
        self.assertListEqual(result.valid_data, [{'a': 0.0, 'b': 0.0}])

        with self.assertRaises(ValidationError) as ctx:
            packer_2.load_many(invalid_data, raise_error=True)
        result = ctx.exception.msg
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, {0: {'c': 'c'}})
        self.assertListEqual(result.valid_data, [{'a': 0.0, 'b': 0.0}])

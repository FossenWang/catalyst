from unittest import TestCase


from catalyst.catalyst import Catalyst
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
        a_data, b_data, c_data = {'a': 0.0}, {'b': 1.0}, {'c': 2.0}
        all_data = {'a': 0.0, 'b': 1.0, 'c': 2.0}

        packer = CatalystPacker((a, b, c))
        data = (a_data, b_data, c_data)

        result = packer.dump(data)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.valid_data, all_data)

        result = packer.load(data)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.valid_data, all_data)

        invalid_data = ({'a': 'a'}, {'b': 'b'}, {'c': 'c'})

        result = packer.dump(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertEqual(set(result.errors), {'b', 'c', 'a'})

        result = packer.dump(invalid_data, all_errors=False)
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
            packer._process_flow('xxx', None)

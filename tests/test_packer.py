from unittest import TestCase


from catalyst.catalyst import Catalyst
from catalyst.fields import FloatField
from catalyst.exceptions import ValidationError


class PackerTest(TestCase):
    def test_pack(self):
        class A(Catalyst):
            a = FloatField()

        class B(Catalyst):
            b = FloatField()

        class C(Catalyst):
            c = FloatField()

        a, b, c = A(), B(), C()
        a_data, b_data, c_data = {'a': 0.0}, {'b': 1.0}, {'c': 2.0}
        all_data = {'a': 0.0, 'b': 1.0, 'c': 2.0}

        packer = a.pack(a_data) \
            .pack(b, b_data) \
            .pack(c, c_data)

        result = packer.dump()
        self.assertDictEqual(result, all_data)
        result = packer.load()
        self.assertDictEqual(result.data, all_data)

        packer.clear()
        packer.pack(a, {'a': 'a'}) \
            .pack(b, {'b': 'b'}) \
            .pack(c, {'c': 'c'})

        with self.assertRaises(ValueError):
            packer.dump()

        result = packer.load()
        self.assertFalse(result.is_valid)
        self.assertEqual(set(result.errors), {'a', 'b', 'c'})

        with self.assertRaises(ValidationError):
            packer.load(raise_error=True)

        with self.assertRaises(ValueError):
            packer.load(collect_errors=False)

from unittest import TestCase

from catalyst.exceptions import ValidationError
from catalyst.utils import (
    snake_to_camel, ErrorMessageMixin, CatalystResult,
    missing, OptionBox
)


class UtilsTest(TestCase):
    def test_snake_to_camel(self):
        snake = 'snake_to_camel'
        camel = 'snakeToCamel'
        self.assertEqual(snake_to_camel(snake), camel)
        self.assertEqual(snake_to_camel('_snake_to_camel_'), camel)
        self.assertEqual(snake_to_camel(''), '')
        self.assertEqual(snake_to_camel('___'), '')

    def test_error_msg(self):
        class A(ErrorMessageMixin):
            default_error_messages = {'a': 'a'}

        class B(A):
            default_error_messages = {'b': 'b'}

        b = B()
        b.collect_error_messages({'c': 'c'})
        self.assertDictEqual(b.error_messages, {'a': 'a', 'b': 'b', 'c': 'c'})

        with self.assertRaises(ValidationError) as context:
            b.error('b')
        self.assertEqual(str(context.exception), 'b')

        with self.assertRaises(ValidationError) as context:
            b.error('x')
        self.assertEqual(str(context.exception), b.unknown_error)

        b.collect_error_messages({'b': 'bb'})
        with self.assertRaises(ValidationError) as context:
            b.error('b')
        self.assertEqual(str(context.exception), 'bb')

    def test_catalyst_result(self):
        result = CatalystResult({}, {}, {})
        self.assertTrue(result.is_valid)
        s = 'CatalystResult(valid_data={}, errors={}, invalid_data={})'
        self.assertEqual(repr(result), s)
        self.assertEqual(str(result), '{}')

        result = CatalystResult(
            valid_data={}, errors={'error': ValidationError('error')}, invalid_data={0: 0})
        self.assertFalse(result.is_valid)
        s = ("CatalystResult(valid_data={}, "
             "errors={'error': ValidationError('error')}, invalid_data={0: 0})")
        self.assertEqual(repr(result), s)
        self.assertDictEqual(result.format_errors(), {'error': 'error'})
        self.assertEqual(str(result), "{'error': 'error'}")

    def test_option_box(self):
        opts = OptionBox()
        with self.assertRaises(ValueError):
            opts.get()
        with self.assertRaises(ValueError):
            opts.get(a=1, b=2)

        class BaseOptions(OptionBox):
            a = 1
            b = 2

        class Options(BaseOptions):
            a = 1
            b = 3
            c = 4

        opts = Options(c=5, d=6)
        self.assertEqual(opts.a, 1)
        self.assertEqual(opts.b, 3)
        self.assertEqual(opts.c, 5)
        self.assertEqual(opts.d, 6)

    def test_others(self):
        self.assertEqual(str(missing), '<catalyst.missing>')

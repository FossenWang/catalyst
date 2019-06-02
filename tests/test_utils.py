from unittest import TestCase

from catalyst.utils import snake_to_camel, ErrorMessageMixin, \
    ensure_staticmethod
from catalyst.exceptions import ValidationError


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

    def test_ensure_staticmethod(self):
        def func():
            pass

        static_func = ensure_staticmethod(func)
        self.assertIs(static_func.__func__, func)
        self.assertIs(static_func, ensure_staticmethod(static_func))
        self.assertIs(ensure_staticmethod(static_func).__func__, func)

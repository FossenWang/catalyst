from unittest import TestCase
from unittest.mock import patch

from catalyst.exceptions import ValidationError
from catalyst.utils import (
    snake_to_camel, ErrorMessageMixin, BaseResult,
    missing
)


class UtilsTest(TestCase):
    def test_snake_to_camel(self):
        snake = 'snake_to_camel'
        camel = 'snakeToCamel'
        self.assertEqual(snake_to_camel(snake), camel)
        self.assertEqual(snake_to_camel('_snake_to_camel_'), camel)
        self.assertEqual(snake_to_camel(''), '')
        self.assertEqual(snake_to_camel('___'), '')

    @patch.dict('catalyst.utils.ErrorMessageMixin.error_messages')
    def test_error_msg(self):
        class A(ErrorMessageMixin):
            error_messages = {'a': 'a'}

        class B(A):
            error_messages = {'b': 'b'}

        b = B()
        b.collect_error_messages({'c': 'c'})
        self.assertDictEqual(b.error_messages, {'a': 'a', 'b': 'b', 'c': 'c'})

        self.assertEqual(str(b.error('b')), 'b')

        with self.assertRaises(AssertionError) as cm:
            b.error('x')
        self.assertTrue(str(cm.exception).endswith(
            'error key "x" does not exist in the "error_messages" dict.'))

        b.collect_error_messages({'b': 'bb'})
        self.assertEqual(str(b.error('b')), 'bb')

        # test change default `error_messages`
        a = A()

        ErrorMessageMixin.error_messages = {1: 1}
        a.collect_error_messages()
        self.assertDictEqual(a.error_messages, {'a': 'a', 1: 1})

        A.error_messages = {2: 2, 'a': 'aaaaa'}
        a.collect_error_messages()
        self.assertDictEqual(a.error_messages, {'a': 'aaaaa', 1: 1, 2: 2})

        del A.error_messages
        del ErrorMessageMixin.error_messages
        a.collect_error_messages()
        self.assertDictEqual(a.error_messages, {})

    def test_base_result(self):
        result = BaseResult({}, {}, {})
        self.assertTrue(result.is_valid)
        s = 'BaseResult(valid_data={}, errors={}, invalid_data={})'
        self.assertEqual(repr(result), s)

        result = BaseResult(
            valid_data={}, errors={'error': ValidationError('error')}, invalid_data={0: 0})
        self.assertFalse(result.is_valid)
        s = ("BaseResult(valid_data={}, "
             "errors={'error': ValidationError('error')}, invalid_data={0: 0})")
        self.assertEqual(repr(result), s)
        self.assertDictEqual(result.format_errors(), {'error': 'error'})

    def test_others(self):
        self.assertEqual(str(missing), '<catalyst.missing>')

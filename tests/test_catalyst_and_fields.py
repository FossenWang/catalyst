from unittest import TestCase

from catalyst.core import Catalyst
from catalyst.exceptions import ValidationError
from catalyst.utils import snake_to_camel, LoadResult
from catalyst.fields import Field, StringField, IntegerField, ListField, NestedField
from catalyst.groups import FieldGroup


class CatalystAndFieldsTest(TestCase):
    """Integration tests for Catalyst and Field and FieldGroup."""

    def test_field_naming_style(self):
        # change field key naming style
        class A(Catalyst):
            _format_field_key = staticmethod(snake_to_camel)
            snake_to_camel = Field()

        self.assertEqual(A.snake_to_camel.name, 'snake_to_camel')
        self.assertEqual(A.snake_to_camel.key, 'snakeToCamel')

        a = A()
        result = a.dump({'snake_to_camel': 'snake'})
        self.assertIn('snakeToCamel', result.valid_data)
        result = a.load({'snakeToCamel': 'snake'})
        self.assertIn('snake_to_camel', result.valid_data)

        # change field name naming style
        class B(Catalyst):
            _format_field_name = staticmethod(snake_to_camel)
            snake_to_camel = Field()

        self.assertEqual(B.snake_to_camel.name, 'snakeToCamel')
        self.assertEqual(B.snake_to_camel.key, 'snake_to_camel')

        b = B()
        result = b.dump({'snakeToCamel': 'snake'})
        self.assertIn('snake_to_camel', result.valid_data)
        result = b.load({'snake_to_camel': 'snake'})
        self.assertIn('snakeToCamel', result.valid_data)

        # change field name and key naming style
        class C(Catalyst):
            _format_field_name = staticmethod(snake_to_camel)
            _format_field_key = staticmethod(snake_to_camel)
            snake_to_camel = Field()
            still_snake = Field(name='still_snake', key='still_snake')

        self.assertEqual(C.snake_to_camel.name, 'snakeToCamel')
        self.assertEqual(C.snake_to_camel.key, 'snakeToCamel')
        self.assertEqual(C.still_snake.name, 'still_snake')
        self.assertEqual(C.still_snake.key, 'still_snake')

        c = C()
        self.assertIs(c._format_field_key, snake_to_camel)
        self.assertIs(c._format_field_name, snake_to_camel)
        result = c.dump({'snakeToCamel': None, 'still_snake': None})
        self.assertIn('snakeToCamel', result.valid_data)
        self.assertIn('still_snake', result.valid_data)
        result = c.load({'snakeToCamel': None, 'still_snake': None})
        self.assertIn('snakeToCamel', result.valid_data)
        self.assertIn('still_snake', result.valid_data)

    def test_field_args_for_dump_and_load(self):
        def create_catalyst(**kwargs):
            class C(Catalyst):
                s = StringField(**kwargs)
            return C()

        def assert_field_dump_args(data, expect=None, **kwargs):
            catalyst = create_catalyst(**kwargs)
            self.assertEqual(catalyst.dump(data, True).valid_data, expect)

        # default dump behavior
        # missing field will raise error
        catalyst = create_catalyst()
        with self.assertRaises(ValidationError):
            catalyst.dump(None, True)
        with self.assertRaises(ValidationError):
            catalyst.dump({}, True)
        # allow None
        assert_field_dump_args({'s': None}, {'s': None})

        # ignore missing field
        assert_field_dump_args({}, {}, dump_required=False)
        assert_field_dump_args(None, {}, dump_required=False)

        # default value for missing field
        assert_field_dump_args({}, {'s': 'default'}, dump_default='default')
        assert_field_dump_args({'s': '1'}, {'s': '1'}, dump_default='default')
        assert_field_dump_args({}, {'s': None}, dump_default=None)
        # callable default
        assert_field_dump_args({}, {'s': '1'}, dump_default=lambda: '1')

        # dump_required has no effect if dump_default is set
        assert_field_dump_args({}, {'s': None}, dump_required=True, dump_default=None)

        # no_dump means ignore this field
        assert_field_dump_args({'s': 1}, {}, no_dump=True)

        def assert_field_load_args(data, expect=None, **kwargs):
            catalyst = create_catalyst(**kwargs)
            self.assertEqual(catalyst.load(data, True).valid_data, expect)

        # default load behavior
        # missing field will be excluded
        assert_field_load_args({}, {})
        # allow None
        assert_field_load_args({'s': None}, {'s': None})

        # default value for missing field
        assert_field_load_args({}, {'s': None}, load_default=None)
        assert_field_load_args({}, {'s': '1'}, load_default=1)
        # callable default
        assert_field_load_args({}, {'s': '1'}, load_default=lambda: 1)

        # invalid when required field is missing
        with self.assertRaises(ValidationError):
            assert_field_load_args({}, load_required=True)

        # load_required has no effect if load_default is set
        assert_field_load_args({}, {'s': None}, load_required=True, load_default=None)

        # always invalid if load_default is None and allow_none is False
        with self.assertRaises(ValidationError):
            assert_field_load_args({}, allow_none=False, load_default=None)

        # no_load means ignore this field
        assert_field_load_args({'s': 1}, {}, no_load=True)

    def test_list_field(self):
        class C(Catalyst):
            nums = ListField(IntegerField())

        c = C()

        data = {'nums': [1, '2', 3.0]}

        result = c.dump(data)
        self.assertEqual(result.valid_data['nums'], [1, 2, 3])

        result = c.load(data)
        self.assertEqual(result.valid_data['nums'], [1, 2, 3])

        data['nums'] = [1, 'x', 3]

        result = c.dump(data)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.valid_data['nums'], [1, 3])
        self.assertEqual(result.invalid_data['nums'][1], 'x')
        self.assertIsInstance(result.errors['nums'][1], ValueError)

        result = c.load(data)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.valid_data['nums'], [1, 3])
        self.assertEqual(result.invalid_data['nums'][1], 'x')
        self.assertIsInstance(result.errors['nums'][1], ValueError)

    def test_nested_field(self):
        class User(Catalyst):
            uid = IntegerField()
            name = StringField()

        user_catalyst = User()

        class Article(Catalyst):
            title = StringField()
            content = StringField()
            author = NestedField(user_catalyst)

        catalyst = Article()

        data = {
            'title': 'x',
            'content': 'x',
            'author': {
                'uid': 1,
                'name': 'x'
            }
        }
        r = catalyst.dump(data)
        self.assertEqual(data, r.valid_data)
        r = catalyst.load(data)
        self.assertEqual(data, r.valid_data)

        invalid_data = {
            'title': 'x',
            'content': 'x',
            'author': {
                'uid': 'x',
                'name': 'x'
            }
        }
        r = catalyst.load(invalid_data)
        self.assertDictEqual(r.valid_data, {'author': {'name': 'x'}, 'content': 'x', 'title': 'x'})
        self.assertDictEqual(r.invalid_data, {'author': {'uid': 'x'}})
        self.assertEqual(set(r.errors['author']), {'uid'})

    def test_field_group(self):
        class C(Catalyst):
            a = IntegerField()
            b = IntegerField()
            no_extra = FieldGroup(declared_fields=('a', 'b'))

            @staticmethod
            @no_extra.set_dump
            def inject_kwargs(data, **kwargs):
                assert set(kwargs) == {'field', 'original_method'}
                return data

            @staticmethod
            @no_extra.set_load
            def check_no_extra(data, original_data, field: FieldGroup = None):
                extra_fields = set(original_data) - set(field.declared_fields)
                if extra_fields:
                    raise ValidationError(f"Invalid fields: '{extra_fields}'.")
                return data

        # test fields injection
        self.assertSetEqual(set(C.no_extra.fields), {'a', 'b'})
        self.assertEqual(C.no_extra.fields['a'], C.a)

        c = C(all_errors=False)

        # test invoking groups
        valid_data = {'a': 1, 'b': 2}
        result = c.load(valid_data)
        self.assertTrue(result.is_valid)
        result = c.dump(valid_data)
        self.assertTrue(result.is_valid)

        # test error handling
        invalid_data = {'a': 1, 'b': 2, 'c': 3}
        result = c.load(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertSetEqual(set(result.errors), {'no_extra'})
        self.assertDictEqual(result.invalid_data, {'a': 1, 'b': 2})

        # test data in BaseResult
        @C.no_extra.set_load
        def raise_error(data):
            raise ValidationError(LoadResult({}, {'x': 'x'}, {}))

        c = C()
        self.assertEqual(c.no_extra.load, raise_error)

        result = c.load(valid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.errors, {'x': 'x'})
        self.assertDictEqual(result.invalid_data, {})

        # test non dict data in BaseResult
        @C.no_extra.set_load
        def raise_error_2(data):
            raise ValidationError(LoadResult(0, 0, 0))

        c = C()
        self.assertEqual(c.no_extra.load, raise_error_2)

        result = c.load(valid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.errors, {'no_extra': '0'})

        # The catalyst should inject fields into FieldGroup only after
        # `Field.name` and `Field.key` of every fields are generated
        class TestSetFields(FieldGroup):
            def set_fields(self, fields):
                super().set_fields(fields)

                field = self.fields['field']
                self.field_name = field.name
                self.field_key = field.key

        class C2(Catalyst):
            group = TestSetFields(declared_fields='*')
            field = IntegerField()

        c = C2()
        self.assertEqual(c.group.field_key, c.field.key)
        self.assertEqual(c.group.field_name, c.field.name)

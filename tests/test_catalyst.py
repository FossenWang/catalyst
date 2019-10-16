from unittest import TestCase

from catalyst import Catalyst
from catalyst.fields import Field, StringField, IntegerField, \
    FloatField, BoolField, CallableField, ListField
from catalyst.exceptions import ValidationError
from catalyst.utils import get_item, \
    snake_to_camel


class TestData:
    def __init__(
            self, string=None, integer=None, float_=None,
            bool_=None, list_=None, obj=None):
        self.string = string
        self.integer = integer
        self.float_ = float_
        self.bool_ = bool_
        self.list_ = list_
        self.obj = obj

    def func(self, a, b, c=1):
        return a + b + c


class TestDataCatalyst(Catalyst):
    string = StringField(min_length=2, max_length=12,
                         dump_default='default', load_default='default')
    integer = IntegerField(min_value=0, max_value=12, load_required=True)
    float_field = FloatField(name='float_', key='float', min_value=-1.1, max_value=1.1)
    bool_field = BoolField(name='bool_', key='bool')
    func = CallableField(name='func', key='func', func_args=(1, 2, 3))
    list_ = ListField(StringField())


test_catalyst = TestDataCatalyst()


class CatalystTest(TestCase):

    def test_inherit(self):
        class A(Catalyst):
            a = Field()

        class B(A):
            b = Field()

        a = A()
        b = B()

        self.assertTrue(hasattr(a, 'a'))
        self.assertTrue(hasattr(b, 'a'))
        self.assertTrue(hasattr(b, 'b'))
        self.assertEqual(b.a, a.a)

        data = {'a': 'a', 'b': 'b'}
        self.assertDictEqual(b.dump(data).valid_data, data)

    def test_change_field_name_and_key_naming_style(self):
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

    def test_init(self):
        "Test initializing Catalyst."

        dump_data = TestData(
            string='xxx', integer=1, float_=1.1,
            bool_=True, list_=['a', 'b'])
        load_data = {
            'string': 'xxx', 'integer': 1, 'float': 1.1,
            'bool': True, 'list_': ['a', 'b']}

        # Empty "fields" has no effect
        catalyst = TestDataCatalyst(fields=[])
        self.assertDictEqual(
            catalyst._dump_field_dict, test_catalyst._dump_field_dict)
        self.assertDictEqual(
            catalyst._load_field_dict, test_catalyst._load_field_dict)
        # if field.no_load is True, this field will be excluded from loading
        self.assertNotIn('func', catalyst._load_field_dict.keys())

        # Specify "fields" for dumping and loading
        catalyst = TestDataCatalyst(fields=['string'])
        self.assertDictEqual(
            catalyst.dump(dump_data).valid_data, {'string': 'xxx'})
        self.assertDictEqual(
            catalyst.load(load_data).valid_data, {'string': 'xxx'})

        # "dump_fields" takes precedence over "fields"
        catalyst = TestDataCatalyst(fields=['string'], dump_fields=['bool_field'])
        self.assertDictEqual(
            catalyst.dump(dump_data).valid_data, {'bool': True})
        self.assertDictEqual(
            catalyst.load(load_data).valid_data, {'string': 'xxx'})

        # "load_fields" takes precedence over "fields"
        catalyst = TestDataCatalyst(fields=['string'], load_fields=['bool_field'])
        self.assertDictEqual(
            catalyst.dump(dump_data).valid_data, {'string': 'xxx'})
        self.assertDictEqual(
            catalyst.load(load_data).valid_data, {'bool_': True})

        # When "dump_fields" and "load_fields" are given, fields is not used.
        catalyst = TestDataCatalyst(
            fields=['integer'], dump_fields=['string'], load_fields=['bool_field'])
        self.assertDictEqual(
            catalyst.dump(dump_data).valid_data, {'string': 'xxx'})
        self.assertDictEqual(
            catalyst.load(load_data).valid_data, {'bool_': True})

        with self.assertRaises(KeyError):
            TestDataCatalyst(fields=['wrong_name'])

        with self.assertRaises(KeyError):
            TestDataCatalyst(dump_fields=['wrong_name'])

        with self.assertRaises(KeyError):
            TestDataCatalyst(load_fields=['wrong_name'])

        dump_data_dict = {
            'float_': 1.1, 'integer': 1, 'string': 'xxx',
            'bool_': True, 'func': dump_data.func, 'list_': ['a', 'b']
        }

        # only get dump value from attribute
        catalyst = TestDataCatalyst(dump_from=getattr)
        catalyst.dump(dump_data)
        with self.assertRaises(ValidationError):
            catalyst.dump(dump_data_dict, True)

        # only get dump value from key
        catalyst = TestDataCatalyst(dump_from=get_item)
        catalyst.dump(dump_data_dict)
        with self.assertRaises(TypeError):
            catalyst.dump(dump_data, all_errors=False)

        # dump_from & load_from must be callable
        with self.assertRaises(TypeError):
            TestDataCatalyst(dump_from='wrong')

        with self.assertRaises(TypeError):
            TestDataCatalyst(load_from='wrong')

    def test_base_dump_and_load(self):
        "Test dumping and loading data."
        # test dump
        dump_data = TestData(
            string='xxx', integer=1, float_=1.1,
            bool_=True, list_=['a', 'b'])

        # dump from object
        result = test_catalyst.dump(dump_data).valid_data
        self.assertDictEqual(result, {
            'bool': True, 'float': 1.1, 'func': 6,
            'integer': 1, 'list_': ['a', 'b'], 'string': 'xxx'})

        # dump from dict
        dump_data_dict = {
            'float_': 1.1, 'integer': 1, 'string': 'xxx',
            'bool_': True, 'func': dump_data.func, 'list_': ['a', 'b']
        }
        self.assertEqual(
            test_catalyst.dump(dump_data_dict).valid_data,
            result)

        # test load
        load_data = {
            'string': 'xxx', 'integer': 1, 'float': 1.1,
            'bool': True, 'list_': ['a', 'b']}
        load_result = {
            'string': 'xxx', 'integer': 1, 'float_': 1.1,
            'bool_': True, 'list_': ['a', 'b']}

        # test valid data
        result = test_catalyst.load(load_data)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.invalid_data, {})
        self.assertDictEqual(result.errors, {})
        self.assertDictEqual(result.valid_data, load_result)

        # test invalid data
        with self.assertRaises(TypeError):
            test_catalyst.load(1)

        # test invalid data: validate errors
        invalid_data = {'string': 'xxx' * 20, 'integer': 100, 'float': 2}
        result = test_catalyst.load(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, invalid_data)
        self.assertEqual(set(result.errors), {
            'string', 'integer', 'float'})
        self.assertDictEqual(result.valid_data, {})

        # test invalid_data: parse errors
        invalid_data = {'string': 'x', 'integer': 'str', 'float': []}
        result = test_catalyst.load(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, invalid_data)
        self.assertEqual(set(result.errors), {
            'string', 'integer', 'float'})
        self.assertIsInstance(result.errors['string'], ValidationError)
        self.assertIsInstance(result.errors['integer'], ValueError)
        self.assertIsInstance(result.errors['float'], TypeError)

        # raise_error & all_errors
        result = test_catalyst.load(
            invalid_data, raise_error=False, all_errors=True)
        self.assertFalse(result.is_valid)
        self.assertEqual(set(result.errors), {'string', 'integer', 'float'})

        result = test_catalyst.load(
            invalid_data, raise_error=False, all_errors=False)
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 1)

        with self.assertRaises(ValidationError) as ctx:
            test_catalyst.load(
                invalid_data, raise_error=True, all_errors=True)
        self.assertEqual(set(ctx.exception.msg.errors), {'string', 'integer', 'float'})

        with self.assertRaises(ValidationError) as ctx:
            test_catalyst.load(
                invalid_data, raise_error=True, all_errors=False)
        self.assertEqual(len(ctx.exception.msg.errors), 1)

        # test field method
        invalid_dump_data = {
            'float_': 1.1, 'integer': '1', 'string': 'xxx',
            'bool_': True, 'func': dump_data.func, 'list_': ['a', 'b']
        }
        # both parse and validate
        result = TestDataCatalyst(dump_method='dump').dump(invalid_dump_data)
        self.assertFalse(result.is_valid)
        self.assertEqual(set(result.invalid_data), {'integer'})
        # only validate, no format
        result = TestDataCatalyst(dump_method='validate').dump(invalid_dump_data)
        self.assertFalse(result.is_valid)
        self.assertEqual(set(result.invalid_data), {'integer'})

        invalid_load_data = {
            'string': 'xxx', 'integer': '1', 'float': 1.1,
            'bool': True, 'list_': ['a', 'b']}
        # only validate, no parse
        result = TestDataCatalyst(load_method='validate').load(invalid_load_data)
        self.assertFalse(result.is_valid)
        self.assertEqual(set(result.invalid_data), {'integer'})
        # only parse, no validate, can force to change type
        result = TestDataCatalyst(load_method='parse').load(invalid_load_data)
        self.assertTrue(result.is_valid)

        with self.assertRaises(ValueError):
            TestDataCatalyst(dump_method=1)

        with self.assertRaises(ValueError):
            TestDataCatalyst(load_method=1)

        # wrong handle name
        with self.assertRaises(ValueError):
            test_catalyst._base_handle(1, {})

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
        with self.assertRaises(ValidationError):
            catalyst.dump({}, True, False)
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

        # pass None to formatter
        assert_field_dump_args({'s': None}, {'s': 'None'}, format_none=True)
        assert_field_dump_args({}, {'s': 'None'}, format_none=True, dump_default=None)
        assert_field_dump_args({'s': None}, {'s': 'None'}, format_none=True, allow_none=False)

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

        # pass None to parser and validators
        assert_field_load_args({'s': None}, {'s': 'None'}, parse_none=True)
        assert_field_load_args({}, {'s': 'None'}, parse_none=True, load_default=None)
        assert_field_load_args({'s': None}, {'s': 'None'}, parse_none=True, allow_none=False)

        # always invalid if load_default is None and allow_none is False
        with self.assertRaises(ValidationError):
            assert_field_load_args({}, allow_none=False, load_default=None)

        # no_load means ignore this field
        assert_field_load_args({'s': 1}, {}, no_load=True)

    def test_pre_and_post_process(self):
        class C(Catalyst):
            max_value = IntegerField()
            min_value = IntegerField()

            def pre_dump(self, obj):
                return self.pre_load(obj)

            def post_dump(self, data):
                return self.post_load(data)

            def pre_load(self, data):
                keys = {field.key for field in self._load_field_dict.values()}
                extra_keys = set(data.keys()) - keys
                if extra_keys:
                    raise ValidationError(f'This keys should not be present: {extra_keys}.')
                return data

            def post_load(self, data):
                if data['max_value'] < data['min_value']:
                    raise ValidationError('"max_value" must be larger than "min_value".')
                return data

        c = C()

        # dump valid
        c.dump({'max_value': 2, 'min_value': 1})

        # pre_dump invalid
        result = c.dump({'max_value': 2, 'min_value': 1, 'xxx': 1})
        self.assertFalse(result.is_valid)
        self.assertTrue('pre_dump' in result.errors)
        with self.assertRaises(ValidationError):
            c.dump({'max_value': 2, 'min_value': 1, 'xxx': 1}, raise_error=True)
        C.pre_dump.error_key = 'not_allowed_keys'
        result = c.dump({'max_value': 2, 'min_value': 1, 'xxx': 1})
        self.assertFalse(result.is_valid)
        self.assertTrue('not_allowed_keys' in result.errors)

        # post_dump invalid
        result = c.dump({'max_value': 1, 'min_value': 2})
        self.assertFalse(result.is_valid)
        self.assertTrue('post_dump' in result.errors)
        with self.assertRaises(ValidationError):
            c.dump({'max_value': 1, 'min_value': 2}, raise_error=True)
        C.post_dump.error_key = 'wrong_value'
        result = c.dump({'max_value': 1, 'min_value': 2})
        self.assertFalse(result.is_valid)
        self.assertTrue('wrong_value' in result.errors)

        # load valid
        result = c.load({'max_value': 2, 'min_value': 1})
        self.assertTrue(result.is_valid)

        # pre_load invalid
        result = c.load({'max_value': 2, 'min_value': 1, 'xxx': 1})
        self.assertFalse(result.is_valid)
        self.assertTrue('pre_load' in result.errors)
        # pre_load error_key
        C.pre_load.error_key = 'not_allowed_keys'
        result = c.load({'max_value': 2, 'min_value': 1, 'xxx': 1})
        self.assertFalse(result.is_valid)
        self.assertTrue('not_allowed_keys' in result.errors)
        # pre_load raise error
        with self.assertRaises(ValidationError) as ctx:
            c.load({'max_value': 2, 'min_value': 1, 'xxx': 1}, raise_error=True)
        self.assertTrue('not_allowed_keys' in ctx.exception.msg.errors)

        # post_load invalid
        result = c.load({'max_value': 1, 'min_value': 2})
        self.assertFalse(result.is_valid)
        self.assertTrue('post_load' in result.errors)
        # post_load error_key
        C.post_load.error_key = 'wrong_value'
        result = c.load({'max_value': 1, 'min_value': 2})
        self.assertFalse(result.is_valid)
        self.assertTrue('wrong_value' in result.errors)

    def test_load_and_dump_args(self):
        class A(Catalyst):
            a = IntegerField()
            b = IntegerField()
            args = ListField(IntegerField())
            class kwargs(Catalyst):
                c = IntegerField()

        a = A()

        @a.load_args
        def func_1(a, *args, b=1, **kwargs):
            return a + sum(args) + b + kwargs['c']

        self.assertEqual(func_1('1', '2', b='3', c='4'), 10)
        # raise error if kwargs are invalid
        with self.assertRaises(ValidationError) as ctx:
            func_1('x', 'x', b='3', c='x')
        self.assertEqual(set(ctx.exception.msg.errors), {'a', 'args', 'kwargs'})

        @a.load_args(all_errors=False)
        def func_2(a, *args, b=1, **kwargs):
            return a + sum(args) + b + kwargs['c']

        self.assertEqual(func_2(1, 2, b=3, c=4), 10)
        # don't collect error
        with self.assertRaises(ValidationError) as ctx:
            func_2('x', 'x', b='3', c='x')
        self.assertEqual(len(ctx.exception.msg.errors), 1)

        @a.dump_args
        def func_3(a, *args, b=1, **kwargs):
            return a + sum(args) + b + kwargs['c']

        self.assertEqual(func_3(1, 2, b=3, c=4), 10)
        self.assertEqual(func_3('1', 2, b=3, c=4), 10)

    def test_load_and_dump_many(self):
        class C(Catalyst):
            s = StringField(min_length=1, max_length=2)

        c = C()

        data = [{'s': 's'} for _ in range(5)]
        result = c.dump_many(data)
        self.assertListEqual(result.valid_data, data)
        result = c.dump_many(data, raise_error=True)
        self.assertTrue(result.is_valid)

        result = c.load_many(data)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.valid_data, data)
        self.assertEqual(result.errors, {})
        self.assertEqual(result.invalid_data, {})

        result = c.load_many(data, raise_error=True)
        self.assertTrue(result.is_valid)

        data[2]['s'] = ''
        data[3]['s'] = 'sss'

        result = c.load_many(data)
        s = "{2: {'s': 'Ensure length >= 1.'}, 3: {'s': 'Ensure length <= 2.'}}"
        self.assertEqual(str(result), s)
        self.assertEqual(set(result.errors), {2, 3})
        self.assertDictEqual(result.invalid_data, {2: {'s': ''}, 3: {'s': 'sss'}})

        with self.assertRaises(ValidationError) as ctx:
            c.load_many(data, raise_error=True)
        result = ctx.exception.msg
        self.assertEqual(set(result.errors), {2, 3})
        self.assertDictEqual(result.invalid_data, {2: {'s': ''}, 3: {'s': 'sss'}})

        with self.assertRaises(ValidationError) as ctx:
            c.load_many(data, True, all_errors=False)
        result = ctx.exception.msg
        self.assertEqual(set(result.errors), {2})
        self.assertDictEqual(result.invalid_data, {2: {'s': ''}})

        # wrong handle name
        with self.assertRaises(ValueError):
            test_catalyst._handle_many(1, [])

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
        data = {
            'title': 'x',
            'content': 'x',
            'author': {
                'uid': 1,
                'name': 'x'
            }
        }

        # Automatic wrap an object of Catalyst as NestedField
        class User(Catalyst):
            uid = IntegerField()
            name = StringField()

        user_catalyst = User()

        class Article1(Catalyst):
            title = StringField()
            content = StringField()
            author = user_catalyst

        catalyst = Article1()

        r = catalyst.dump(data)
        self.assertEqual(data, r.valid_data)
        r = catalyst.load(data)
        self.assertEqual(data, r.valid_data)

        # Automatic wrap a subclass of Catalyst as NestedField
        class Article2(Catalyst):
            title = StringField()
            content = StringField()

            class author(Catalyst):
                uid = IntegerField()
                name = StringField()

        catalyst = Article2()

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

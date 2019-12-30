from unittest import TestCase

from catalyst.core import (
    BaseCatalyst,
    CatalystMeta,
    Catalyst,
)
from catalyst.fields import Field, String, Integer, \
    Float, Boolean, Method, List
from catalyst.exceptions import ValidationError
from catalyst.utils import snake_to_camel


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
    string = String(min_length=2, max_length=12,
                    dump_default='default', load_default='default')
    integer = Integer(minimum=0, maximum=12, load_required=True)
    float_field = Float(name='float_', key='float', minimum=-1.1, maximum=1.1)
    bool_field = Boolean(name='bool_', key='bool')
    func = Method(name='func', key='func', func_args=(1, 2, 3))
    list_ = List(String())


test_catalyst = TestDataCatalyst()


class CatalystTest(TestCase):

    def test_inherit(self):
        class A(Catalyst):
            a = Field()
            b = Field()

            class Options(Catalyst.Options):
                all_errors = False

        class B(A):
            b = Integer()
            c = Float()

            class Options(A.Options):
                raise_error = True

        a = A()
        b = B()

        self.assertEqual(set(a._field_dict), {'a', 'b'})
        self.assertEqual(set(b._field_dict), {'a', 'b', 'c'})
        self.assertIsInstance(a._field_dict['b'], Field)
        self.assertIsInstance(b._field_dict['b'], Integer)

        data = {'a': 'a', 'b': 'b'}
        self.assertDictEqual(a.dump(data).valid_data, data)

        data = {'a': 'a', 'b': 1, 'c': 1.0}
        self.assertDictEqual(b.dump(data).valid_data, data)

        self.assertEqual(a.opts.all_errors, False)
        self.assertEqual(a.opts.raise_error, False)
        self.assertEqual(b.opts.all_errors, False)
        self.assertEqual(b.opts.raise_error, True)

        # wrong type for Options
        with self.assertRaises(TypeError):
            CatalystMeta('X', (object,), {'Options': object})

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

    def test_set_fields_by_non_class_inheritance(self):
        # test fields from class inheritance
        self.assertNotIn('schema', repr(test_catalyst))
        self.assertIsNone(test_catalyst.opts.schema)
        self.assertIs(test_catalyst.integer, test_catalyst._field_dict['integer'])

        # set fields from a non `Catalyst` class when instantiate
        class Schema:
            a = String()
            b = Float()

            @staticmethod
            @b.set_formatter
            def test(value):
                return value

        catalyst = Catalyst(Schema)
        fields = catalyst._field_dict
        self.assertIn('schema', repr(catalyst))
        self.assertIs(fields['a'], Schema.a)
        self.assertIs(fields['b'], Schema.b)
        # setting opts of field works
        self.assertIsNone(Schema.b.formatter(None))
        self.assertIs(Schema.b.formatter, Schema.test)

        # instance also works
        catalyst = TestDataCatalyst(Schema())
        fields = catalyst._field_dict
        self.assertIn('schema', repr(catalyst))
        self.assertIs(fields['a'], Schema.a)
        self.assertIs(fields['b'], Schema.b)

        # inheritance works
        class Schema2:
            a = String()
            string = Float()
        catalyst = TestDataCatalyst(Schema2)
        fields = catalyst._field_dict
        self.assertIs(fields['string'], Schema2.string)
        self.assertIsNot(fields['string'], TestDataCatalyst.string)

        with self.assertRaises(NotImplementedError):
            BaseCatalyst._set_fields(1, 1)

    def test_base_dump_and_load(self):
        "Test dumping and loading data."
        # test dump
        dump_data = TestData(
            string='xxx', integer=1, float_=1.1,
            bool_=True, list_=['a', 'b'])

        # dump from object
        result = test_catalyst.dump(dump_data)
        self.assertDictEqual(result.valid_data, {
            'bool': True, 'float': 1.1, 'func': 6,
            'integer': 1, 'list_': ['a', 'b'], 'string': 'xxx'})

        # dump from dict
        dump_data_dict = {
            'float_': 1.1, 'integer': 1, 'string': 'xxx',
            'bool_': True, 'func': dump_data.func, 'list_': ['a', 'b']
        }
        self.assertEqual(
            test_catalyst.dump(dump_data_dict).valid_data,
            result.valid_data)

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
        self.assertFalse(result.errors)
        self.assertFalse(result.invalid_data)
        self.assertDictEqual(result.valid_data, load_result)

        # test invalid data: wrong type
        result = test_catalyst.load(1)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.valid_data, {})
        self.assertEqual(result.invalid_data, 1)
        self.assertEqual(set(result.errors), {'load'})

        # test error_keys
        test_catalyst.opts.error_keys = {'load': 'xxx'}
        result = test_catalyst.load(1)
        self.assertFalse(result.is_valid)
        self.assertEqual(set(result.errors), {'xxx'})

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
        # with self.assertRaises(ValueError):
        #     test_catalyst._process_flow(1, False, {})
        # with self.assertRaises(ValueError):
        #     test_catalyst._process_one(1, {}, True)

    def test_field_args_for_dump_and_load(self):
        def create_catalyst(**kwargs):
            class C(Catalyst):
                s = String(**kwargs)
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
            max_value = Integer()
            min_value = Integer()

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

            def pre_load_many(self, data):
                assert len(data) < 3
                return data

        c = C()

        valid_data = {'max_value': 2, 'min_value': 1}
        # dump valid
        c.dump(valid_data)

        # pre_dump invalid
        redundant_data = {'max_value': 2, 'min_value': 1, 'xxx': 1}
        result = c.dump(redundant_data)
        self.assertFalse(result.is_valid)
        self.assertTrue('pre_dump' in result.errors)
        with self.assertRaises(ValidationError):
            c.dump(redundant_data, raise_error=True)
        c.opts.error_keys = {'pre_dump': 'not_allowed_keys'}
        result = c.dump(redundant_data)
        self.assertFalse(result.is_valid)
        self.assertTrue('not_allowed_keys' in result.errors)

        # post_dump invalid
        invalid_data = {'max_value': 1, 'min_value': 2}
        result = c.dump(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertTrue('post_dump' in result.errors)
        with self.assertRaises(ValidationError):
            c.dump(invalid_data, raise_error=True)
        c.opts.error_keys = {'post_dump': 'wrong_value'}
        result = c.dump(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertTrue('wrong_value' in result.errors)

        # load valid
        result = c.load(valid_data)
        self.assertTrue(result.is_valid)

        # pre_load invalid
        result = c.load(redundant_data)
        self.assertFalse(result.is_valid)
        self.assertTrue('pre_load' in result.errors)
        # pre_load error_key
        c.opts.error_keys = {'pre_load': 'not_allowed_keys'}
        result = c.load(redundant_data)
        self.assertFalse(result.is_valid)
        self.assertTrue('not_allowed_keys' in result.errors)
        # pre_load raise error
        with self.assertRaises(ValidationError) as ctx:
            c.load(redundant_data, raise_error=True)
        self.assertTrue('not_allowed_keys' in ctx.exception.msg.errors)

        # post_load invalid
        result = c.load(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertTrue('post_load' in result.errors)
        # post_load error_key
        c.opts.error_keys = {'post_load': 'wrong_value'}
        result = c.load(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertTrue('wrong_value' in result.errors)

        # post_load invalid
        result = c.load_many([valid_data, invalid_data])
        self.assertFalse(result.is_valid)
        self.assertTrue('wrong_value' in result.errors[1])
        self.assertDictEqual(result.invalid_data[1], invalid_data)

        # pre_load_many invalid
        result = c.load_many([{}, {}, {}])
        self.assertFalse(result.is_valid)
        self.assertFalse(result.valid_data)
        self.assertTrue('pre_load_many' in result.errors)
        self.assertListEqual(result.invalid_data, [{}, {}, {}])

    def test_load_and_dump_args(self):
        class A(Catalyst):
            a = Integer()
            b = Integer()
            args = List(Integer())
            class kwargs(Catalyst):
                c = Integer()

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
            s = String(min_length=1, max_length=2)

        c = C()

        data = [{'s': 's'} for _ in range(5)]
        result = c.dump_many(data)
        self.assertListEqual(result.valid_data, data)
        result = c.dump_many(data, raise_error=True)
        self.assertTrue(result.is_valid)

        result = c.load_many(data)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.valid_data, data)
        self.assertFalse(result.errors)
        self.assertFalse(result.invalid_data)

        result = c.load_many(data, raise_error=True)
        self.assertTrue(result.is_valid)

        data[2]['s'] = ''
        data[3]['s'] = 'sss'

        result = c.load_many(data)
        s = "{2: {'s': 'Length must >= 1.'}, 3: {'s': 'Length must <= 2.'}}"
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

        result = c.load_many(1)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.valid_data, [])
        self.assertEqual(result.invalid_data, 1)
        self.assertEqual(set(result.errors), {'load_many'})

        result = c.load_many([1, {}])
        self.assertFalse(result.is_valid)
        self.assertEqual(result.valid_data, [{}, {}])
        self.assertEqual(result.invalid_data, {0: 1})
        self.assertEqual(set(result.errors), {0})
        self.assertEqual(set(result.errors[0]), {'load'})

        c.opts.error_keys = {'load_many': 'xxx'}
        result = c.load_many(1)
        self.assertFalse(result.is_valid)
        self.assertEqual(set(result.errors), {'xxx'})

    def test_list_field(self):
        class C(Catalyst):
            nums = List(Integer())

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

        # Automatic wrap an object of Catalyst as Nested
        class User(Catalyst):
            uid = Integer()
            name = String()

        user_catalyst = User()

        class Article1(Catalyst):
            title = String()
            content = String()
            author = user_catalyst

        catalyst = Article1()

        r = catalyst.dump(data)
        self.assertEqual(data, r.valid_data)
        r = catalyst.load(data)
        self.assertEqual(data, r.valid_data)

        # Automatic wrap a subclass of Catalyst as Nested
        class Article2(Catalyst):
            title = String()
            content = String()

            class author(Catalyst):
                uid = Integer()
                name = String()

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

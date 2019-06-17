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


test_data_catalyst = TestDataCatalyst(raise_error=False)


class CatalystTest(TestCase):

    def setUp(self):
        self.test_data = TestData(
            string='xxx', integer=1, float_=1.1,
            bool_=True, list_=['a', 'b'])

        self.valid_data = {
            'string': 'xxx', 'integer': 1, 'float': 1.1,
            'bool': True, 'list_': ['a', 'b']}

        self.load_result = {
            'string': 'xxx', 'integer': 1, 'float_': 1.1,
            'bool_': True, 'list_': ['a', 'b']}

    def create_catalyst(self, **kwargs):
        class C(Catalyst):
            s = StringField(**kwargs)
        return C()

    def assert_field_dump_args(self, data, result=None, **kwargs):
        catalyst = self.create_catalyst(**kwargs)
        self.assertEqual(catalyst.dump(data, True).valid_data, result)

    def test_metaclass(self):
        "Test metaclass of Catalyst."

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

    def test_init(self):
        "Test initializing Catalyst."

        test_data = self.test_data
        valid_data = self.valid_data

        # Empty "fields" has no effect
        catalyst = TestDataCatalyst(fields=[])
        self.assertDictEqual(
            catalyst._dump_field_dict, test_data_catalyst._dump_field_dict)
        self.assertDictEqual(
            catalyst._load_field_dict, test_data_catalyst._load_field_dict)
        # if field.no_load is True, this field will be excluded from loading
        self.assertNotIn('func', catalyst._load_field_dict.keys())

        # Specify "fields" for dumping and loading
        catalyst = TestDataCatalyst(fields=['string'])
        self.assertDictEqual(
            catalyst.dump(test_data).valid_data, {'string': 'xxx'})
        self.assertDictEqual(
            catalyst.load(valid_data).valid_data, {'string': 'xxx'})

        # "dump_fields" takes precedence over "fields"
        catalyst = TestDataCatalyst(fields=['string'], dump_fields=['bool_field'])
        self.assertDictEqual(
            catalyst.dump(test_data).valid_data, {'bool': True})
        self.assertDictEqual(
            catalyst.load(valid_data).valid_data, {'string': 'xxx'})

        # "load_fields" takes precedence over "fields"
        catalyst = TestDataCatalyst(fields=['string'], load_fields=['bool_field'])
        self.assertDictEqual(
            catalyst.dump(test_data).valid_data, {'string': 'xxx'})
        self.assertDictEqual(
            catalyst.load(valid_data).valid_data, {'bool_': True})

        # When "dump_fields" and "load_fields" are given, fields is not used.
        catalyst = TestDataCatalyst(
            fields=['integer'], dump_fields=['string'], load_fields=['bool_field'])
        self.assertDictEqual(
            catalyst.dump(test_data).valid_data, {'string': 'xxx'})
        self.assertDictEqual(
            catalyst.load(valid_data).valid_data, {'bool_': True})

        with self.assertRaises(KeyError):
            TestDataCatalyst(fields=['wrong_name'])

        with self.assertRaises(KeyError):
            TestDataCatalyst(dump_fields=['wrong_name'])

        with self.assertRaises(KeyError):
            TestDataCatalyst(load_fields=['wrong_name'])

    def test_base_dumping(self):
        "Test dumping data."

        test_data = self.test_data

        # dump from object
        result = test_data_catalyst.dump(test_data).valid_data
        self.assertDictEqual(result, {
            'bool': True, 'float': 1.1, 'func': 6,
            'integer': 1, 'list_': ['a', 'b'], 'string': 'xxx'})

        # dump from dict
        test_data_dict = {
            'float_': 1.1, 'integer': 1, 'string': 'xxx',
            'bool_': True, 'func': test_data.func, 'list_': ['a', 'b']
        }
        self.assertEqual(
            test_data_catalyst.dump(test_data_dict).valid_data,
            result)

        # only get dump value from attribute
        catalyst = TestDataCatalyst(dump_from=getattr)
        catalyst.dump(test_data)
        with self.assertRaises(ValidationError):
            catalyst.dump(test_data_dict, True)

        # only get dump value from key
        catalyst = TestDataCatalyst(dump_from=get_item)
        catalyst.dump(test_data_dict)
        with self.assertRaises(TypeError):
            catalyst.dump(test_data, collect_errors=False)

        # wrong args
        with self.assertRaises(TypeError):
            catalyst = TestDataCatalyst(dump_from='wrong')

    def test_field_args_which_affect_dumping(self):
        # default behavior
        # missing field will raise error
        with self.assertRaises(ValidationError):
            self.assert_field_dump_args(None)
        with self.assertRaises(ValidationError):
            self.assert_field_dump_args({})

        # ignore missing field
        self.assert_field_dump_args({}, {}, dump_required=False)

        # default value for missing field
        self.assert_field_dump_args(
            {}, {'s': 'default'}, dump_default='default')

        self.assert_field_dump_args(
            {'s': '1'}, {'s': '1'}, dump_default='default')

        self.assert_field_dump_args(
            {}, {'s': None}, dump_default=None)

        # callable default
        self.assert_field_dump_args(
            {}, {'s': '1'}, dump_default=lambda: '1')

        # dump_required has no effect if dump_default is set
        with self.assertWarns(Warning):
            self.assert_field_dump_args(
                {}, {'s': None}, dump_required=True, dump_default=None)

        # pass None to formatter
        self.assert_field_dump_args(
            {'s': None}, {'s': 'None'}, format_none=True)

        self.assert_field_dump_args(
            {}, {'s': 'None'}, format_none=True, dump_default=None)

        # no_dump means ignore this field
        self.assert_field_dump_args({1: 1}, {}, no_dump=True)

    def test_base_loading(self):
        "Test loading data."

        valid_data = self.valid_data
        load_result = self.load_result

        # test valid_data
        result = test_data_catalyst.load(valid_data)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.invalid_data, {})
        self.assertDictEqual(result.errors, {})
        self.assertDictEqual(result.valid_data, load_result)

        # test invalid_data
        with self.assertRaises(TypeError):
            test_data_catalyst.load(1)

        # test invalid_data: validate errors
        invalid_data = {'string': 'xxx' * 20, 'integer': 100, 'float': 2}
        result = test_data_catalyst.load(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, invalid_data)
        self.assertEqual(set(result.errors), {
            'string', 'integer', 'float'})
        self.assertDictEqual(result.valid_data, {})

        # test invalid_data: parse errors
        invalid_data = {'string': 'x', 'integer': 'str', 'float': []}
        result = test_data_catalyst.load(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, invalid_data)
        self.assertEqual(set(result.errors), {
            'string', 'integer', 'float'})
        self.assertIsInstance(result.errors['string'], ValidationError)
        self.assertIsInstance(result.errors['integer'], ValueError)
        self.assertIsInstance(result.errors['float'], TypeError)

        # raise error while validating
        # set "raise_error" when init
        raise_err_catalyst = TestDataCatalyst(raise_error=True)
        result = raise_err_catalyst.load(valid_data)
        self.assertTrue(result.is_valid)
        with self.assertRaises(ValidationError):
            raise_err_catalyst.load(invalid_data)

        # set "raise_error" when call load
        with self.assertRaises(ValidationError):
            test_data_catalyst.load(invalid_data, raise_error=True)

        # don't collect errors
        # set "collect_errors" when init
        no_collect_err_catalyst = TestDataCatalyst(collect_errors=False)
        with self.assertRaises(Exception):
            no_collect_err_catalyst.load(invalid_data)

        # set "collect_errors" when call load
        result = no_collect_err_catalyst.load(invalid_data, collect_errors=True, raise_error=False)
        self.assertFalse(result.is_valid)

        # set "collect_errors" when call load
        with self.assertRaises(Exception):
            test_data_catalyst.load(invalid_data, collect_errors=False)

    def test_field_args_which_affect_loading(self):

        # default behavior
        # missing field will be excluded
        catalyst = self.create_catalyst()
        result = catalyst.load({})
        self.assertTrue(result.is_valid)
        self.assertEqual(result.valid_data, {})

        # default value for missing field
        catalyst = self.create_catalyst(load_default=None)
        result = catalyst.load({})
        self.assertTrue(result.is_valid)
        self.assertEqual(result.valid_data['s'], None)

        result = catalyst.load({'s': 1})
        self.assertTrue(result.is_valid)
        self.assertEqual(result.valid_data['s'], '1')

        catalyst = self.create_catalyst(load_default=1)
        result = catalyst.load({})
        self.assertTrue(result.is_valid)
        self.assertEqual(result.valid_data['s'], '1')

        # callable default
        catalyst = self.create_catalyst(load_default=lambda: 1)
        result = catalyst.load({})
        self.assertTrue(result.is_valid)
        self.assertEqual(result.valid_data['s'], '1')

        # invalid when required field is missing
        catalyst = self.create_catalyst(load_required=True)
        result = catalyst.load({})
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.valid_data, {})
        self.assertDictEqual(result.invalid_data, {})
        self.assertEqual(set(result.errors), {'s'})

        # load_required has no effect if load_default is set
        with self.assertWarns(Warning):
            catalyst = self.create_catalyst(load_required=True, load_default=None)
        result = catalyst.load({})
        self.assertTrue(result.is_valid)
        self.assertEqual(result.valid_data['s'], None)

        # pass None to parser and validators
        catalyst = self.create_catalyst(parse_none=True)
        result = catalyst.load({'s': None})
        self.assertTrue(result.is_valid)
        self.assertEqual(result.valid_data['s'], 'None')

        catalyst = self.create_catalyst(parse_none=True, load_default=None)
        result = catalyst.load({})
        self.assertTrue(result.is_valid)
        self.assertEqual(result.valid_data['s'], 'None')

        catalyst = self.create_catalyst(parse_none=True, allow_none=False)
        result = catalyst.load({'s': None})
        self.assertTrue(result.is_valid)
        self.assertEqual(result.valid_data['s'], 'None')

        # always invalid if load_default is None and allow_none is False
        catalyst = self.create_catalyst(allow_none=False, load_default=None)
        result = catalyst.load({})
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.valid_data, {})
        self.assertDictEqual(result.invalid_data, {'s': None})
        self.assertEqual(set(result.errors), {'s'})

        # no_load means ignore this field
        class CC(Catalyst):
            s = StringField(no_load=True)

        catalyst = CC()

        result = catalyst.load({})
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.valid_data, {})

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
        with self.assertRaises(ValidationError):
            c.load({'max_value': 2, 'min_value': 1, 'xxx': 1}, raise_error=True)
        with self.assertRaises(ValidationError):
            c.load({'max_value': 2, 'min_value': 1, 'xxx': 1}, collect_errors=False)

        # post_load invalid
        result = c.load({'max_value': 1, 'min_value': 2})
        self.assertFalse(result.is_valid)
        self.assertTrue('post_load' in result.errors)
        # post_load error_key
        C.post_load.error_key = 'wrong_value'
        result = c.load({'max_value': 1, 'min_value': 2})
        self.assertFalse(result.is_valid)
        self.assertTrue('wrong_value' in result.errors)

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

    def test_load_and_dump_kwargs(self):
        class A(Catalyst):
            a = IntegerField()
            b = IntegerField()
            c = IntegerField()

        a = A()

        @a.load_kwargs
        def func_1(a, b=1, **kwargs):
            return a + b + kwargs['c']

        self.assertEqual(func_1(a='1', b='2', c='3'), 6)
        # raise error if kwargs are invalid
        with self.assertRaises(ValidationError):
            func_1(a='a', b='2', c='3')
        # takes kwargs only
        with self.assertRaises(TypeError):
            func_1('1', b='2', c='3')

        @a.load_kwargs(collect_errors=False)
        def func_2(a, b=1, **kwargs):
            return a + b + kwargs['c']

        self.assertEqual(func_2(a='1', b='2', c='3'), 6)
        # don't collect error
        with self.assertRaises(ValueError):
            func_2(a='a')

        @a.dump_kwargs
        def func_3(a, b=1, **kwargs):
            return a + b + kwargs['c']

        self.assertEqual(func_3(a=1, b=2, c=3), 6)
        # raise error if kwargs are invalid
        with self.assertRaises(ValidationError):
            func_3(a='1', b=2, c=3)
        # takes kwargs only
        with self.assertRaises(TypeError):
            func_3(1, b=2, c=3)

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
        with self.assertRaises(ValidationError):
            func_1('a', '2', b='3', c='4')

        @a.load_args(collect_errors=False)
        def func_2(a, *args, b=1, **kwargs):
            return a + sum(args) + b + kwargs['c']

        self.assertEqual(func_2(1, 2, b=3, c=4), 10)
        # don't collect error
        with self.assertRaises(ValueError):
            func_2('a', '2', b='3', c='4')

        @a.dump_args
        def func_3(a, *args, b=1, **kwargs):
            return a + sum(args) + b + kwargs['c']

        self.assertEqual(func_3(1, 2, b=3, c=4), 10)
        # raise error if kwargs are invalid
        with self.assertRaises(ValidationError):
            func_3('1', 2, b=3, c=4)

    def test_load_and_dump_many(self):
        c = self.create_catalyst(min_length=1, max_length=2)

        data = [{'s': 's'} for _ in range(5)]
        result = c.dump_many(data)
        self.assertListEqual(result.valid_data, data)

        result = c.load_many(data)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.valid_data, data)
        self.assertEqual(result.errors, {})
        self.assertEqual(result.invalid_data, {})

        data[2]['s'] = ''
        data[3]['s'] = 'sss'

        result = c.load_many(data)
        s = "{2: {'s': 'Ensure length >= 1.'}, 3: {'s': 'Ensure length <= 2.'}}"
        self.assertEqual(str(result), s)
        self.assertEqual(set(result.errors), {2, 3})
        self.assertDictEqual(result.invalid_data, {2: {'s': ''}, 3: {'s': 'sss'}})

        with self.assertRaises(ValidationError) as ct:
            c.load_many(data, raise_error=True)
        result = ct.exception.msg
        self.assertEqual(set(result.errors), {2, 3})
        self.assertDictEqual(result.invalid_data, {2: {'s': ''}, 3: {'s': 'sss'}})

        with self.assertRaises(ValidationError) as ct:
            c.load_many(data, collect_errors=False)
        self.assertIsInstance(ct.exception.msg, str)

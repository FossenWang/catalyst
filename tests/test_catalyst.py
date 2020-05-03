from unittest import TestCase

from catalyst.base import CatalystABC
from catalyst.core import Catalyst
from catalyst.fields import Field, StringField, IntegerField, \
    FloatField, BooleanField, CallableField, ListField, NestedField
from catalyst.exceptions import ValidationError


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
    string = StringField(
        min_length=2, max_length=12, dump_default='default', load_default='default')
    integer = IntegerField(minimum=0, maximum=12, load_required=True)
    float_field = FloatField(name='float_', key='float', minimum=-1.1, maximum=1.1)
    bool_field = BooleanField(name='bool_', key='bool')
    func = CallableField(name='func', key='func', func_args=(1, 2, 3))
    list_ = ListField(StringField())


test_catalyst = TestDataCatalyst()


class CatalystTest(TestCase):
    def test_abstract_catalyst(self):
        abstract_catalyst = CatalystABC()
        with self.assertRaises(NotImplementedError):
            abstract_catalyst.dump(None)
        with self.assertRaises(NotImplementedError):
            abstract_catalyst.load(None)
        with self.assertRaises(NotImplementedError):
            abstract_catalyst.dump_many(None)
        with self.assertRaises(NotImplementedError):
            abstract_catalyst.load_many(None)

    def test_inherit(self):
        class A(Catalyst):
            all_errors = False

            a = Field()
            b = Field()

        class B(A):
            raise_error = True

            b = IntegerField()
            c = FloatField()

        a = A()
        b = B()

        self.assertListEqual(list(a.fields), ['a', 'b'])
        self.assertListEqual(list(b.fields), ['a', 'b', 'c'])
        self.assertIsInstance(a.fields['b'], Field)
        self.assertIsInstance(b.fields['b'], IntegerField)

        data = {'a': 'a', 'b': 'b'}
        self.assertDictEqual(a.dump(data).valid_data, data)

        data = {'a': 'a', 'b': 1, 'c': 1.0}
        self.assertDictEqual(b.dump(data).valid_data, data)

        self.assertEqual(a.all_errors, False)
        self.assertEqual(a.raise_error, False)
        self.assertEqual(b.all_errors, False)
        self.assertEqual(b.raise_error, True)

        class C:
            c = StringField()

        class CB(C, B):
            pass

        self.assertListEqual(list(CB.fields), ['a', 'b', 'c'])
        self.assertIsInstance(CB.fields['c'], StringField)

        class BC(B, C):
            pass

        self.assertListEqual(list(BC.fields), ['c', 'a', 'b'])
        self.assertIsInstance(BC.fields['c'], FloatField)

        class D(C):
            d = FloatField()

        class DB(D, B):
            pass

        self.assertListEqual(list(DB.fields), ['a', 'b', 'c', 'd'])
        self.assertIsInstance(DB.fields['c'], StringField)
        self.assertIsInstance(DB.fields['d'], FloatField)

        class BD(B, D):
            pass

        self.assertListEqual(list(BD.fields), ['c', 'd', 'a', 'b'])
        self.assertIsInstance(BD.fields['c'], FloatField)
        self.assertIsInstance(BD.fields['d'], FloatField)

    def test_set_fields_by_schema(self):
        # wrong type
        with self.assertRaises(TypeError):
            Catalyst({'x': Field})

        class A:
            a = FloatField()

            @staticmethod
            @a.set_formatter
            def test(value):
                return value + 1

        # set fields from schema which is non Catalyst class
        catalyst = Catalyst(A)
        self.assertIs(catalyst.fields['a'], A.a)
        # setting opts of field works
        self.assertEqual(A.a.dump(1), 2)
        self.assertIs(A.a.formatter, A.test)

        # set fields from FieldDict
        catalyst = Catalyst({'a': A.a})
        self.assertIs(catalyst.fields['a'], A.a)

        # class inheritance, fields following method resolution order
        class B:
            base = IntegerField()
            a = IntegerField()
            b = IntegerField()

        class AB(A, B):
            pass

        catalyst = Catalyst(AB)
        fields = catalyst.fields
        self.assertListEqual(list(fields), ['base', 'a', 'b'])
        self.assertIsInstance(fields['a'], FloatField)

        class BA(B, A):
            pass

        catalyst = Catalyst(BA)
        fields = catalyst.fields
        self.assertListEqual(list(fields), ['a', 'base', 'b'])
        self.assertIsInstance(fields['a'], IntegerField)

        # fields of schema override fields of Catalyst class
        class Base(Catalyst):
            base = Field()

        catalyst = Base(BA)
        fields = catalyst.fields
        self.assertListEqual(list(fields), ['base', 'a', 'b'])
        self.assertIsInstance(fields['base'], IntegerField)

        # set fields from schema which is Catalyst class
        class BABase(BA, Base):
            pass

        catalyst = Catalyst(BABase)
        fields = catalyst.fields
        self.assertListEqual(list(fields), ['base', 'a', 'b'])
        self.assertIsInstance(fields['base'], IntegerField)

        # set fields from schema which is Catalyst instance
        catalyst = Catalyst(BABase())
        fields = catalyst.fields
        self.assertListEqual(list(fields), ['base', 'a', 'b'])
        self.assertIsInstance(fields['base'], IntegerField)

        # set fields from schema which is non Catalyst instance
        catalyst = Catalyst(BA())
        fields = catalyst.fields
        # fields following alphabetic order
        self.assertListEqual(list(fields), ['a', 'b', 'base'])
        self.assertIsInstance(fields['a'], IntegerField)

    def test_init(self):
        dump_data = TestData(
            string='xxx', integer=1, float_=1.1,
            bool_=True, list_=['a', 'b'])
        load_data = {
            'string': 'xxx', 'integer': 1, 'float': 1.1,
            'bool': True, 'list_': ['a', 'b']}

        # Empty `include`
        catalyst = TestDataCatalyst(include=[])
        self.assertDictEqual(catalyst._dump_fields, {})
        self.assertDictEqual(catalyst._load_fields, {})

        # if field.no_load is True, this field will be excluded from loading
        self.assertNotIn('func', test_catalyst._load_fields.keys())

        # Specify `include` for dumping and loading
        catalyst = TestDataCatalyst(include=['string'])
        self.assertDictEqual(
            catalyst.dump(dump_data).valid_data, {'string': 'xxx'})
        self.assertDictEqual(
            catalyst.load(load_data).valid_data, {'string': 'xxx'})

        # `dump_include` takes precedence over `include`
        catalyst = TestDataCatalyst(include=['string'], dump_include=['bool_field'])
        self.assertDictEqual(
            catalyst.dump(dump_data).valid_data, {'bool': True})
        self.assertDictEqual(
            catalyst.load(load_data).valid_data, {'string': 'xxx'})

        # `load_include` takes precedence over `include`
        catalyst = TestDataCatalyst(include=['string'], load_include=['bool_field'])
        self.assertDictEqual(
            catalyst.dump(dump_data).valid_data, {'string': 'xxx'})
        self.assertDictEqual(
            catalyst.load(load_data).valid_data, {'bool_': True})

        # When `dump_include` and `load_include` are given, `include` is not used.
        catalyst = TestDataCatalyst(
            include=['integer'], dump_include=['string'], load_include=['bool_field'])
        self.assertDictEqual(
            catalyst.dump(dump_data).valid_data, {'string': 'xxx'})
        self.assertDictEqual(
            catalyst.load(load_data).valid_data, {'bool_': True})

        # Specify `exclude` for dumping and loading
        catalyst = TestDataCatalyst(exclude=['string'])
        self.assertNotIn('string', catalyst._dump_fields)
        self.assertNotIn('string', catalyst._load_fields)

        # When `dump_exclude` and `load_exclude` are given, `exclude` is not used.
        catalyst = TestDataCatalyst(
            exclude=['integer'], dump_exclude=['string'], load_exclude=['bool_field'])
        self.assertIn('integer', catalyst._dump_fields)
        self.assertIn('integer', catalyst._dump_fields)
        self.assertNotIn('string', catalyst._dump_fields)
        self.assertNotIn('bool_field', catalyst._load_fields)

        # Specify `include` and `exclude` at one time
        catalyst = TestDataCatalyst(include=['string', 'integer'], exclude=['string'])
        self.assertIn('integer', catalyst._dump_fields)
        self.assertNotIn('string', catalyst._dump_fields)
        self.assertIn('integer', catalyst._load_fields)
        self.assertNotIn('string', catalyst._load_fields)

        # raise wrong `include`
        with self.assertRaises(ValueError):
            TestDataCatalyst(include=['wrong_name'])
        with self.assertRaises(ValueError):
            TestDataCatalyst(dump_include=['wrong_name'])
        with self.assertRaises(ValueError):
            TestDataCatalyst(load_include=['wrong_name'])

        # ignore wrong `exclude`
        TestDataCatalyst(exclude=['wrong_name'])
        TestDataCatalyst(dump_exclude=['wrong_name'])
        TestDataCatalyst(load_exclude=['wrong_name'])

    def test_dump_and_load(self):
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

        # test process_aliases
        test_catalyst.process_aliases['load'] = 'xxx'
        result = test_catalyst.load(1)
        self.assertFalse(result.is_valid)
        self.assertEqual(set(result.errors), {'xxx'})
        test_catalyst.process_aliases.clear()

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
        result = test_catalyst.load(invalid_data, raise_error=False)
        self.assertFalse(result.is_valid)
        self.assertEqual(set(result.errors), {'string', 'integer', 'float'})

        with self.assertRaises(ValidationError) as ctx:
            test_catalyst.load(invalid_data, raise_error=True)
        self.assertEqual(set(ctx.exception.msg.errors), {'string', 'integer', 'float'})

        catalyst_2 = TestDataCatalyst(all_errors=False)
        result = catalyst_2.load(invalid_data, raise_error=False)
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 1)

        with self.assertRaises(ValidationError) as ctx:
            catalyst_2.load(invalid_data, raise_error=True)
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

        # wrong process name
        with self.assertRaises(ValueError):
            test_catalyst._make_processor(1, False)

    def test_load_and_dump_args(self):
        class Kwargs(Catalyst):
            c = IntegerField()
        class A(Catalyst):
            a = IntegerField()
            b = IntegerField()
            args = ListField(IntegerField())
            kwargs = NestedField(Kwargs())

        a = A()

        @a.load_args
        def func_1(a, *args, b=1, **kwargs):
            return a + sum(args) + b + kwargs['c']

        self.assertEqual(func_1('1', '2', b='3', c='4'), 10)
        # raise error if kwargs are invalid
        with self.assertRaises(ValidationError) as ctx:
            func_1('x', 'x', b='3', c='x')
        self.assertEqual(set(ctx.exception.msg.errors), {'a', 'args', 'kwargs'})

        @a.dump_args
        def func_3(a, *args, b=1, **kwargs):
            return a + sum(args) + b + kwargs['c']

        self.assertEqual(func_3(1, 2, b=3, c=4), 10)
        self.assertEqual(func_3('1', 2, b=3, c=4), 10)

        a_2 = A(all_errors=False)
        @a_2.load_args
        def func_2(a, *args, b=1, **kwargs):
            return a + sum(args) + b + kwargs['c']

        self.assertEqual(func_2(1, 2, b=3, c=4), 10)
        # don't collect error
        with self.assertRaises(ValidationError) as ctx:
            func_2('x', 'x', b='3', c='x')
        self.assertEqual(len(ctx.exception.msg.errors), 1)

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
        self.assertFalse(result.errors)
        self.assertFalse(result.invalid_data)

        result = c.load_many(data, raise_error=True)
        self.assertTrue(result.is_valid)

        data[2]['s'] = ''
        data[3]['s'] = 'sss'

        result = c.load_many(data)
        self.assertEqual(set(result.errors), {2, 3})
        self.assertDictEqual(result.invalid_data, {2: {'s': ''}, 3: {'s': 'sss'}})

        with self.assertRaises(ValidationError) as ctx:
            c.load_many(data, raise_error=True)
        result = ctx.exception.msg
        self.assertEqual(set(result.errors), {2, 3})
        self.assertDictEqual(result.invalid_data, {2: {'s': ''}, 3: {'s': 'sss'}})

        c_2 = C(all_errors=False)
        result = c_2.load_many(data)
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


        c = C(process_aliases={'load_many': 'xxx'})
        result = c.load_many(1)
        self.assertFalse(result.is_valid)
        self.assertEqual(set(result.errors), {'xxx'})

    def test_pre_and_post_process(self):
        class C(Catalyst):
            max_value = IntegerField()
            min_value = IntegerField()

            def pre_dump(self, obj):
                return self.pre_load(obj)

            def post_dump(self, data, original_data):
                assert original_data is not None
                return self.post_load(data)

            def pre_load(self, data):
                keys = {field.key for field in self._load_fields.values()}
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
        result = c.dump(valid_data)
        self.assertTrue(result.is_valid)

        # pre_dump invalid
        redundant_data = {'max_value': 2, 'min_value': 1, 'xxx': 1}
        result = c.dump(redundant_data)
        self.assertFalse(result.is_valid)
        self.assertTrue('pre_dump' in result.errors)
        with self.assertRaises(ValidationError):
            c.dump(redundant_data, raise_error=True)
        c.process_aliases['pre_dump'] = 'not_allowed_keys'
        result = c.dump(redundant_data)
        self.assertFalse(result.is_valid)
        self.assertTrue('not_allowed_keys' in result.errors)

        # post_dump invalid
        invalid_data = {'max_value': 1, 'min_value': 2}
        result = c.dump(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertEqual({'post_dump'}, set(result.errors))

        c.process_aliases['post_dump'] = 'wrong_value'
        result = c.dump(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertEqual({'wrong_value'}, set(result.errors))

        # load valid
        result = c.load(valid_data)
        self.assertTrue(result.is_valid)

        # pre_load invalid
        result = c.load(redundant_data)
        self.assertFalse(result.is_valid)
        self.assertTrue('pre_load' in result.errors)
        # pre_load error key
        c.process_aliases['pre_load'] = 'not_allowed_keys'
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
        # post_load error key
        c.process_aliases['post_load'] = 'wrong_value'
        result = c.load(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertTrue('wrong_value' in result.errors)

        # post_load invalid
        result = c.load_many([valid_data, invalid_data])
        self.assertFalse(result.is_valid)
        self.assertTrue('wrong_value' in result.errors[1])
        self.assertDictEqual(result.invalid_data[1], invalid_data)

        # shouldn't execute post_load when load raises error
        result = c.load({'max_value': 'x', 'min_value': 2})
        self.assertFalse(result.is_valid)
        self.assertFalse('wrong_value' in result.errors)
        self.assertTrue('max_value' in result.errors)

        # pre_load_many invalid
        result = c.load_many([{}, {}, {}])
        self.assertFalse(result.is_valid)
        self.assertFalse(result.valid_data)
        self.assertTrue('pre_load_many' in result.errors)
        self.assertListEqual(result.invalid_data, [{}, {}, {}])

        c.process_aliases.clear()

    def test_except_exception(self):
        catalyst = Catalyst(
            schema={'a': IntegerField(minimum=0)},
            except_exception=(ValueError, ValidationError))

        result = catalyst.load({'a': 'x'})
        self.assertFalse(result.is_valid)
        self.assertIsInstance(result.errors['a'], ValueError)

        result = catalyst.load({'a': -1})
        self.assertFalse(result.is_valid)
        self.assertIsInstance(result.errors['a'], ValidationError)

        with self.assertRaises(TypeError):
            catalyst.load(1)

        with self.assertRaises(TypeError):
            catalyst.load({'a': []})

from unittest import TestCase
from datetime import datetime, time, date

from catalyst import Catalyst
from catalyst.fields import (
    Field, StringField, IntegerField, FloatField,
    BoolField, ListField, CallableField,
    DatetimeField, TimeField, DateField,
    NestField,
)
from catalyst.validators import ValidationError


class TestData:
    def __init__(self, string=None, integer=None, float_=None, bool_=None,
                 time=None):
        self.string = string
        self.integer = integer
        self.float_ = float_
        self.bool_ = bool_
        self.time = time

    def func(self, a, b, c=1):
        return a + b + c


class FieldTest(TestCase):
    def test_field(self):
        class A(Catalyst):
            fixed_value = Field()
            key_1 = Field()
            key_2 = Field()

            @staticmethod
            @key_1.set_dump_from
            @key_2.set_dump_from
            def from_dict_key(obj, name):
                return obj[name]

            @staticmethod
            @fixed_value.set_formatter
            def fixed_value_formatter(value):
                return 1

            @fixed_value.set_parse
            def parse_fixed_value(value):
                return value + 1

            @fixed_value.set_validators
            def large_than(value):
                assert value > 0
                return value + 1  # 返回值无用

            @fixed_value.add_validator
            def less_than(value):
                assert value < 100

        # test formatter
        field_1 = Field(formatter=A.fixed_value_formatter)
        self.assertEqual(field_1.formatter, A.fixed_value_formatter)
        a = A()
        test_data = TestData()
        test_data.fixed_value = 'asd'
        self.assertEqual(a.fixed_value.dump(test_data), 1)
        test_data.fixed_value = 1000
        self.assertEqual(a.fixed_value.dump(test_data), 1)
        test_data.fixed_value = [100]
        self.assertEqual(a.fixed_value.dump(test_data), 1)

        # test dump_from
        field_2 = Field(dump_from=A.from_dict_key)
        self.assertEqual(field_2.dump_from, A.from_dict_key)
        self.assertEqual(a.key_1.dump({'key_1': 1,}), 1)
        self.assertEqual(a.key_2.dump({'key_2': 2,}), 2)
        test_data.key = 1
        self.assertRaises(TypeError, a.key_1.dump, test_data)

        # test load
        self.assertEqual(a.fixed_value.load({'fixed_value': 0}), 1)
        self.assertRaises(TypeError, a.fixed_value.load, {'fixed_value': '0'})
        self.assertRaises(AssertionError, a.fixed_value.load, {'fixed_value': -1})
        self.assertRaises(AssertionError, a.fixed_value.load, {'fixed_value': 100})
        self.assertEqual(len(a.fixed_value.validators), 2)

        # test error msg
        field_3 = Field(key='a', allow_none=False, error_messages={'allow_none': '666'})
        try:
            field_3.load({'a': None})
        except ValidationError as e:
            self.assertEqual(e.msg, '666')

    def test_string_field(self):
        string_field = StringField(name='string', key='string', min_length=2, max_length=12)

        # dump
        test_data = TestData(string='xxx')
        self.assertEqual(string_field.dump(test_data), 'xxx')
        test_data.string = 1
        self.assertEqual(string_field.dump(test_data), '1')
        test_data.string = []
        self.assertEqual(string_field.dump(test_data), '[]')
        test_data.string = None
        self.assertEqual(string_field.dump(test_data), None)

        # load
        self.assertEqual(string_field.load({'string': 'xxx'}), 'xxx')
        self.assertEqual(string_field.load({'string': 123}), '123')
        self.assertEqual(string_field.load({'string': [1]}), '[1]')
        self.assertEqual(string_field.load({'string': None}), None)
        self.assertEqual(string_field.load({}), None)
        self.assertRaises(ValidationError, string_field.load, {'string': ''})

        string_field.allow_none = False
        self.assertRaises(ValidationError, string_field.load, {'string': None})

        string_field.required = True
        self.assertRaises(ValidationError, string_field.load, {})

    def test_int_field(self):
        int_field = IntegerField(name='integer', key='integer', min_value=-10, max_value=100)

        # dump
        test_data = TestData(integer=1)
        self.assertEqual(int_field.dump(test_data), 1)
        test_data.integer = 1.6
        self.assertEqual(int_field.dump(test_data), 1)
        test_data.integer = '10'
        self.assertEqual(int_field.dump(test_data), 10)

        # load
        self.assertEqual(int_field.load({'integer': 0}), 0)
        self.assertEqual(int_field.load({'integer': 1}), 1)
        self.assertEqual(int_field.load({'integer': '1'}), 1)
        self.assertEqual(int_field.load({'integer': None}), None)
        self.assertEqual(int_field.load({}), None)

        self.assertRaises(ValueError, int_field.load, {'integer': ''})
        self.assertRaises(ValidationError, int_field.load, {'integer': 111})
        self.assertRaises(ValueError, int_field.load, {'integer': 'asd'})
        self.assertRaises(TypeError, int_field.load, {'integer': []})

    def test_float_field(self):
        float_field = FloatField(name='float_', key='float', min_value=-11.1, max_value=111.1)

        # dump
        test_data = TestData(float_=1)
        self.assertEqual(float_field.dump(test_data), 1.0)
        test_data.float_ = 0
        self.assertEqual(float_field.dump(test_data), 0.0)
        test_data.float_ = 5.5
        self.assertEqual(float_field.dump(test_data), 5.5)
        test_data.float_ = '10'
        self.assertEqual(float_field.dump(test_data), 10.0)
        test_data.float_ = None
        self.assertEqual(float_field.dump(test_data), None)

        # load
        self.assertEqual(float_field.load({'float': 0}), 0.0)
        self.assertEqual(float_field.load({'float': '1.1'}), 1.1)
        self.assertEqual(float_field.load({'float': -11.1}), -11.1)
        self.assertEqual(float_field.load({'float': 111.1}), 111.1)
        self.assertEqual(float_field.load({'float': 11}), 11)
        self.assertEqual(float_field.load({'float': None}), None)
        self.assertEqual(float_field.load({}), None)

        self.assertRaises(ValueError, float_field.load, {'float': ''})
        self.assertRaises(ValidationError, float_field.load, {'float': 111.11})
        self.assertRaises(TypeError, float_field.load, {'float': []})

    def test_bool_field(self):
        bool_field = BoolField(name='bool_', key='bool')

        # dump
        test_data = TestData(bool_=True)
        self.assertEqual(bool_field.dump(test_data), True)
        test_data.bool_ = False
        self.assertEqual(bool_field.dump(test_data), False)
        test_data.bool_ = None
        self.assertEqual(bool_field.dump(test_data), None)

        # load
        self.assertEqual(bool_field.load({'bool': True}), True)
        self.assertEqual(bool_field.load({'bool': False}), False)
        self.assertEqual(bool_field.load({'bool': 'False'}), True)
        self.assertEqual(bool_field.load({'bool': 0}), False)
        self.assertEqual(bool_field.load({'bool': 1}), True)
        self.assertEqual(bool_field.load({'bool': []}), False)

    def test_list_field(self):
        list_field = ListField(name='list_', key='list', item_field=FloatField(), required=True)

        # dump
        test_data = TestData()
        test_data.list_ = [1, 2, 3]
        self.assertListEqual(list_field.dump(test_data), [1.0, 2.0, 3.0])
        test_data.list_ = []
        self.assertListEqual(list_field.dump(test_data), [])
        test_data.list_ = None
        self.assertEqual(list_field.dump(test_data), None)

        # load
        self.assertListEqual(list_field.load({'list': [1, 2, 3]}), [1.0, 2.0, 3.0])
        self.assertListEqual(list_field.load({'list': []}), [])
        self.assertEqual(list_field.load({'list': None}), None)
        try:
            list_field.load({'any': 1})
        except ValidationError as e:
            self.assertEqual(e.msg, Field.default_error_messages['required'])
        try:
            list_field.load({'list': 1})
        except ValidationError as e:
            self.assertEqual(e.msg, ListField.default_error_messages['iterable'])

    def test_callable_field(self):
        callable_field = CallableField(name='func', func_args=[1, 2], func_kwargs={'c': 3})
        # dump
        test_data = TestData()
        self.assertEqual(callable_field.dump(test_data), 6)

    def test_datetime_field(self):
        def base_test(now, type_, FieldClass, fmt):
            test_data = TestData(time=now)

            field = FieldClass(name='time', key='time')
            dt_str = field.dump(test_data)
            self.assertEqual(dt_str, now.isoformat())
            self.assertEqual(field.load({'time': dt_str}), type_.fromisoformat(dt_str))
            self.assertRaises(ValueError, field.load, {'time': '2018'})

            field = FieldClass(name='time', key='time', fmt=fmt)
            dt_str = field.dump(test_data)
            self.assertEqual(dt_str, now.strftime(fmt))
            if type_ is datetime:
                dt = datetime.strptime(dt_str, fmt)
            elif type_ is time:
                dt = datetime.strptime(dt_str, fmt).time()
            elif type_ is date:
                dt = datetime.strptime(dt_str, fmt).date()
            self.assertEqual(field.load({'time': dt_str}), dt)
            self.assertRaises(ValueError, field.load, {'time': '2018Y'})

        now = datetime.now()
        base_test(now, datetime, DatetimeField, '%Y%m%d%H%M%S')
        base_test(now.time(), time, TimeField, '%H%M%S')
        base_test(now.date(), date, DateField, '%Y%m%d')

    def test_nest_field(self):
        class A:
            def __init__(self, name):
                self.name = name

        class B:
            def __init__(self, a):
                self.a = a

        class ACatalyst(Catalyst):
            name = StringField(max_length=3, required=True)
        a_cata = ACatalyst()
        field = NestField(a_cata, name='a', key='a')

        b = B(A('1'))
        self.assertEqual(field.dump(b), {'name': '1'})
        self.assertEqual(field.load({'a': {'name': '1'}}), {'name': '1'})
        self.assertRaises(ValidationError, field.load, {'a': {'n': 'm'}})
        self.assertRaises(ValidationError, field.load, {'a': {'name': '1234'}})
        self.assertRaises(TypeError, field.load, {'a': 1})

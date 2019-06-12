from unittest import TestCase
from datetime import datetime, time, date, timedelta

from catalyst import Catalyst
from catalyst.fields import (
    Field, StringField, IntegerField, FloatField,
    BoolField, ListField, CallableField,
    DatetimeField, TimeField, DateField,
    NestedField,
)
from catalyst.exceptions import ValidationError


class FieldTest(TestCase):
    def test_field(self):
        class A:
            fixed_value = Field(validators=[])

            @staticmethod
            @fixed_value.set_formatter
            def fixed_value_formatter(value):
                return 1

            @staticmethod
            @fixed_value.set_parser
            def fixed_value_add_1(value):
                return value + 1

            @staticmethod
            @fixed_value.set_validators
            def large_than(value):
                assert value > 0
                return value + 1  # 返回值无用

            @staticmethod
            @fixed_value.add_validator
            def less_than(value):
                assert value < 100

        # test dump
        field_1 = Field(formatter=A.fixed_value_formatter)
        self.assertEqual(field_1.formatter, A.fixed_value_formatter)
        a = A()
        self.assertEqual(a.fixed_value.dump('asd'), 1)
        self.assertEqual(a.fixed_value.dump(1000), 1)
        self.assertEqual(a.fixed_value.dump([100]), 1)

        # test load
        self.assertEqual(a.fixed_value.load(0), 1)
        self.assertEqual(a.fixed_value.load(None), None)
        with self.assertRaises(TypeError):
            a.fixed_value.load('0')
        with self.assertRaises(AssertionError):
            a.fixed_value.load(-1)
        with self.assertRaises(AssertionError):
            a.fixed_value.load(100)

        # test validators
        self.assertEqual(len(a.fixed_value.validators), 2)
        with self.assertRaises(TypeError):
            a.fixed_value.set_validators(1)
        with self.assertRaises(TypeError):
            a.fixed_value.add_validator(1)

        # test error msg
        field_3 = Field(key='a', allow_none=False, error_messages={'none': '666'})
        with self.assertRaises(ValidationError) as c:
            field_3.load(None)
        self.assertEqual(c.exception.msg, '666')

    def test_string_field(self):
        string_field = StringField(name='string', key='string', min_length=2, max_length=12)

        # dump
        self.assertEqual(string_field.dump('xxx'), 'xxx')
        self.assertEqual(string_field.dump(1), '1')
        self.assertEqual(string_field.dump([]), '[]')
        self.assertEqual(string_field.dump(None), None)

        # load
        self.assertEqual(string_field.load('xxx'), 'xxx')
        self.assertEqual(string_field.load(123), '123')
        self.assertEqual(string_field.load([1]), '[1]')
        self.assertEqual(string_field.load(None), None)
        with self.assertRaises(ValidationError):
            string_field.load('')

        string_field.allow_none = False
        with self.assertRaises(ValidationError):
            string_field.load(None)

    def test_int_field(self):
        int_field = IntegerField(name='integer', key='integer', min_value=-10, max_value=100)

        # dump
        self.assertEqual(int_field.dump(1), 1)
        self.assertEqual(int_field.dump(1.6), 1)
        self.assertEqual(int_field.dump('10'), 10)

        # load
        self.assertEqual(int_field.load(0), 0)
        self.assertEqual(int_field.load(1), 1)
        self.assertEqual(int_field.load('1'), 1)
        self.assertEqual(int_field.load(None), None)

        with self.assertRaises(ValueError):
            int_field.load('')
        with self.assertRaises(ValidationError):
            int_field.load(111)
        with self.assertRaises(ValueError):
            int_field.load('asd')
        with self.assertRaises(TypeError):
            int_field.load([])

    def test_float_field(self):
        float_field = FloatField(name='float_', key='float', min_value=-11.1, max_value=111.1)

        # dump
        self.assertEqual(float_field.dump(1), 1.0)
        self.assertEqual(float_field.dump(0), 0.0)
        self.assertEqual(float_field.dump(5.5), 5.5)
        self.assertEqual(float_field.dump('10'), 10.0)
        self.assertEqual(float_field.dump(None), None)

        # load
        self.assertEqual(float_field.load(0), 0.0)
        self.assertEqual(float_field.load('1.1'), 1.1)
        self.assertEqual(float_field.load(-11.1), -11.1)
        self.assertEqual(float_field.load(111.1), 111.1)
        self.assertEqual(float_field.load(11), 11)
        self.assertEqual(float_field.load(None), None)

        with self.assertRaises(ValueError):
            float_field.load('')
        with self.assertRaises(ValidationError):
            float_field.load(111.11)
        with self.assertRaises(TypeError):
            float_field.load([])

    def test_bool_field(self):
        bool_field = BoolField(name='bool_', key='bool')

        # dump
        self.assertEqual(bool_field.dump(True), True)
        self.assertEqual(bool_field.dump(False), False)
        self.assertEqual(bool_field.dump(None), None)

        # load
        self.assertEqual(bool_field.load(True), True)
        self.assertEqual(bool_field.load(False), False)
        self.assertEqual(bool_field.load('False'), True)
        self.assertEqual(bool_field.load(0), False)
        self.assertEqual(bool_field.load(1), True)
        self.assertEqual(bool_field.load([]), False)

    def test_list_field(self):
        list_field = ListField(item_field=FloatField())

        # dump
        self.assertListEqual(list_field.dump([1, 2, 3]), [1.0, 2.0, 3.0])
        self.assertListEqual(list_field.dump([]), [])
        self.assertEqual(list_field.dump(None), None)
        with self.assertRaises(TypeError):
            list_field.dump(1)

        # load
        self.assertListEqual(list_field.load([1, 2, 3]), [1.0, 2.0, 3.0])
        self.assertListEqual(list_field.load([]), [])
        with self.assertRaises(TypeError):
            list_field.load(1)
        self.assertIsNone(list_field.load(None))
        list_field.allow_none = False
        with self.assertRaises(ValidationError) as c:
            list_field.load(None)
        self.assertEqual(c.exception.msg, list_field.error_messages['none'])

    def test_callable_field(self):
        callable_field = CallableField(
            name='test_func', func_args=[1, 2], func_kwargs={'c': 3})

        def test_func(a, b, c=1):
            return a + b + c

        # dump
        self.assertEqual(callable_field.dump(test_func), 6)
        callable_field.set_args(4, 5, 3)
        self.assertEqual(callable_field.dump(test_func), 12)
        with self.assertRaises(TypeError):
            callable_field.dump(1)

        # init
        CallableField()
        with self.assertRaises(TypeError):
            CallableField(func_args=0)
        with self.assertRaises(TypeError):
            CallableField(func_kwargs=0)

    def test_datetime_field(self):
        dt = datetime(2019, 1, 1)
        invalid_dt = dt + timedelta(days=1, seconds=1)
        self.base_test_datetime_field(
            dt, invalid_dt, datetime, DatetimeField, '%Y%m%d%H%M%S')
        self.base_test_datetime_field(
            dt.time(), invalid_dt.time(), time, TimeField, '%H%M%S')
        self.base_test_datetime_field(
            dt.date(), invalid_dt.date(), date, DateField, '%Y%m%d')

    def base_test_datetime_field(
            self, dt, invalid_dt, type_, FieldClass, fmt):
        # dump
        field = FieldClass()
        dt_str = field.dump(dt)
        self.assertEqual(dt_str, dt.strftime(field._default_fmt))

        field = FieldClass(fmt=fmt)
        dt_str = field.dump(dt)
        self.assertEqual(dt_str, dt.strftime(fmt))

        # load
        field = FieldClass(max_time=dt)
        dt_str = field.dump(dt)
        self.assertEqual(field.load(dt_str), dt)
        with self.assertRaises(ValueError):
            field.load('2018Y')
        with self.assertRaises(ValidationError):
            dt_str = field.dump(invalid_dt)
            field.load(dt_str)

    def test_nest_field(self):
        class A:
            def __init__(self, name):
                self.name = name

        class ACatalyst(Catalyst):
            name = StringField(max_length=3, load_required=True)
        a_cata = ACatalyst(raise_error=True)
        field = NestedField(a_cata, name='a', key='a')

        self.assertEqual(field.dump(A('1')), {'name': '1'})
        self.assertEqual(field.load({'name': '1'}), {'name': '1'})
        with self.assertRaises(ValidationError):
            field.load({'n': 'm'})
        with self.assertRaises(ValidationError):
            field.load({'name': '1234'})
        with self.assertRaises(TypeError):
            field.load(1)

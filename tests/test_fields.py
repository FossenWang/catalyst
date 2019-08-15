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
        self.assertEqual(field_1.opts.formatter, A.fixed_value_formatter)
        a = A()
        self.assertEqual(a.fixed_value.format(1000), 1)
        with self.assertRaises(AssertionError):
            a.fixed_value.dump(1000)
        self.assertEqual(a.fixed_value.format('asd'), 1)
        with self.assertRaises(TypeError):
            a.fixed_value.dump('asd')

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
        self.assertEqual(len(a.fixed_value.opts.validators), 2)

        # test wrong args
        with self.assertRaises(TypeError):
            a.fixed_value.set_validators(1)
        with self.assertRaises(TypeError):
            a.fixed_value.add_validator(1)
        with self.assertRaises(TypeError):
            a.fixed_value.set_formatter(1)
        with self.assertRaises(TypeError):
            a.fixed_value.set_parser(1)

        # test error msg
        field_3 = Field(key='a', allow_none=False, error_messages={'none': '666'})
        with self.assertRaises(ValidationError) as ctx:
            field_3.load(None)
        self.assertEqual(ctx.exception.msg, '666')


    def test_string_field(self):
        field = StringField(name='string', key='string', min_length=2, max_length=12)

        # dump
        self.assertEqual(field.dump('xxx'), 'xxx')
        with self.assertRaises(TypeError):
            field.dump(1)
        self.assertEqual(field.format(1), '1')
        self.assertEqual(field.format([]), '[]')
        self.assertEqual(field.format(None), None)

        # load
        self.assertEqual(field.load('xxx'), 'xxx')
        self.assertEqual(field.load(123), '123')
        self.assertEqual(field.load([1]), '[1]')
        self.assertEqual(field.load(None), None)
        with self.assertRaises(ValidationError):
            field.load('')

        field.opts.allow_none = False
        with self.assertRaises(ValidationError):
            field.load(None)

    def test_int_field(self):
        field = IntegerField(name='integer', key='integer', min_value=-10, max_value=100)

        # dump
        self.assertEqual(field.dump(1), 1)
        with self.assertRaises(TypeError):
            field.dump(1.6)
        self.assertEqual(field.format(1.6), 1)
        self.assertEqual(field.format('10'), 10)

        # load
        self.assertEqual(field.load(0), 0)
        self.assertEqual(field.load(1), 1)
        self.assertEqual(field.load('1'), 1)
        self.assertEqual(field.load(None), None)

        with self.assertRaises(ValueError):
            field.load('')
        with self.assertRaises(ValidationError):
            field.load(111)
        with self.assertRaises(ValueError):
            field.load('asd')
        with self.assertRaises(TypeError):
            field.load([])

    def test_float_field(self):
        field = FloatField(name='float_', key='float', min_value=-11.1, max_value=111.1)

        # dump
        self.assertEqual(field.dump(5.5), 5.5)
        with self.assertRaises(TypeError):
            field.dump(1)
        self.assertEqual(field.format(1), 1.0)
        self.assertEqual(field.format(0), 0.0)
        self.assertEqual(field.format('10'), 10.0)
        self.assertEqual(field.format(None), None)

        # load
        self.assertEqual(field.load(0), 0.0)
        self.assertEqual(field.load('1.1'), 1.1)
        self.assertEqual(field.load(-11.1), -11.1)
        self.assertEqual(field.load(111.1), 111.1)
        self.assertEqual(field.load(11), 11)
        self.assertEqual(field.load(None), None)

        with self.assertRaises(ValueError):
            field.load('')
        with self.assertRaises(ValidationError):
            field.load(111.11)
        with self.assertRaises(TypeError):
            field.load([])

    def test_bool_field(self):
        field = BoolField(name='bool_', key='bool')

        # dump
        self.assertEqual(field.dump(True), True)
        self.assertEqual(field.dump(False), False)
        self.assertEqual(field.dump(None), None)
        with self.assertRaises(TypeError):
            field.dump(1)

        # load
        self.assertEqual(field.load(True), True)
        self.assertEqual(field.load(False), False)
        self.assertEqual(field.load('False'), True)
        self.assertEqual(field.load(0), False)
        self.assertEqual(field.load(1), True)
        self.assertEqual(field.load([]), False)

    def test_list_field(self):
        field = ListField(item_field=FloatField())

        # dump
        self.assertListEqual(field.dump([1.0, 2.0, 3.0]), [1.0, 2.0, 3.0])
        self.assertListEqual(field.dump([]), [])
        self.assertEqual(field.dump(None), None)
        with self.assertRaises(TypeError):
            field.dump([1, 2, 3])
        with self.assertRaises(TypeError):
            field.dump(1)

        # load
        self.assertListEqual(field.load([1, 2, 3]), [1.0, 2.0, 3.0])
        self.assertListEqual(field.load([]), [])
        with self.assertRaises(TypeError):
            field.load(1)
        self.assertIsNone(field.load(None))
        field.opts.allow_none = False
        with self.assertRaises(ValidationError) as c:
            field.load(None)
        self.assertEqual(c.exception.msg, field.error_messages['none'])

    def test_callable_field(self):
        field = CallableField(
            name='test_func', func_args=[1, 2], func_kwargs={'c': 3})

        def test_func(a, b, c=1):
            return a + b + c

        # dump
        self.assertEqual(field.dump(test_func), 6)
        field.set_args(4, 5, 3)
        self.assertEqual(field.dump(test_func), 12)
        with self.assertRaises(TypeError):
            field.dump(1)

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
        self.assertEqual(dt_str, dt.strftime(field.opts.fmt))

        field = FieldClass(fmt=fmt)
        dt_str = field.dump(dt)
        self.assertEqual(dt_str, dt.strftime(fmt))

        with self.assertRaises(TypeError):
            field.dump(1)

        # load & dump
        field = FieldClass(max_time=dt)
        dt_str = field.dump(dt)
        self.assertEqual(field.load(dt_str), dt)
        with self.assertRaises(ValueError):
            field.load('2018Y')
        with self.assertRaises(ValidationError):
            field.dump(invalid_dt)

    def test_nest_field(self):
        class ACatalyst(Catalyst):
            name = StringField(max_length=3, load_required=True)
        a_cata = ACatalyst(load_raise_error=False)
        field = NestedField(a_cata, name='a', key='a')

        self.assertEqual(field.dump({'name': '1'}), {'name': '1'})
        self.assertEqual(field.dump({'name': '1234'}), {'name': '1234'})
        with self.assertRaises(ValidationError):
            field.dump({'n': 'm'})
        with self.assertRaises(TypeError):
            field.dump(1)

        self.assertEqual(field.load({'name': '1'}), {'name': '1'})
        with self.assertRaises(ValidationError):
            field.load({'n': 'm'})
        with self.assertRaises(ValidationError):
            field.load({'name': '1234'})
        with self.assertRaises(TypeError):
            field.load(1)

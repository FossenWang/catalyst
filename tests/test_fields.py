from decimal import Decimal, ROUND_CEILING
from unittest import TestCase
from datetime import datetime, timedelta

from catalyst import Catalyst
from catalyst.fields import (
    Field, StringField, IntegerField, FloatField,
    BooleanField, ListField, CallableField,
    DatetimeField, TimeField, DateField,
    NestedField, DecimalField,
)
from catalyst.exceptions import ValidationError


class FieldTest(TestCase):
    def test_field(self):
        # test set field opts in class
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
                return value + 1  # useless return

            @staticmethod
            @fixed_value.add_validator
            def less_than(value):
                assert value < 100

        a = A()

        # test dump
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
        self.assertEqual(len(a.fixed_value.validators), 2)

        # test wrong args
        with self.assertRaises(TypeError):
            a.fixed_value.set_validators(1)
        with self.assertRaises(TypeError):
            a.fixed_value.add_validator(1)
        with self.assertRaises(TypeError):
            a.fixed_value.set_formatter(1)
        with self.assertRaises(TypeError):
            a.fixed_value.set_parser(1)

        # test set opts when init field
        field = Field(
            formatter=A.fixed_value_formatter,
            parser=a.fixed_value.parser)
        self.assertEqual(field.formatter, A.fixed_value_formatter)
        self.assertEqual(field.parser, A.fixed_value_add_1)

        # test error msg
        field = Field(key='a', allow_none=False, error_messages={'none': '666'})
        with self.assertRaises(ValidationError) as ctx:
            field.load(None)
        self.assertEqual(ctx.exception.msg, '666')

    def test_string_field(self):
        field = StringField(
            name='string', key='string', min_length=2, max_length=12,
            error_messages={'too_small': 'Must >= {self.minimum}'})

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
        with self.assertRaises(ValidationError) as ctx:
            field.load('')

        # change validator's error message
        self.assertEqual(ctx.exception.msg, 'Must >= 2')
        self.assertEqual(
            field.error_messages['too_small'],
            field.validators[0].error_messages['too_small'])

        field.allow_none = False
        with self.assertRaises(ValidationError):
            field.load(None)

        # match regex
        field = StringField(
            regex='a',
            error_messages={'no_match': 'not match "{self.regex.pattern}"'})
        self.assertEqual(field.load('a'), 'a')

        with self.assertRaises(ValidationError) as ctx:
            field.load('')
        self.assertEqual(ctx.exception.msg, 'not match "a"')

    def test_int_field(self):
        field = IntegerField(
            name='integer', key='integer', minimum=-10, maximum=100,
            error_messages={'too_large': '{self.maximum}'})

        # dump
        self.assertEqual(field.dump(1), 1)
        self.assertEqual(field.format(1.6), 1)
        self.assertEqual(field.format('10'), 10)

        # load
        self.assertEqual(field.load(0), 0)
        self.assertEqual(field.load(1), 1)
        self.assertEqual(field.load('1'), 1)
        self.assertEqual(field.load(None), None)

        with self.assertRaises(ValidationError) as ctx:
            field.load(111)
        self.assertEqual(ctx.exception.msg, '100')
        with self.assertRaises(ValueError):
            field.load('')
        with self.assertRaises(ValueError):
            field.load('asd')
        with self.assertRaises(TypeError):
            field.load([])

    def test_float_field(self):
        field = FloatField(name='float_', key='float', minimum=-11.1, maximum=111.1)

        # dump
        self.assertEqual(field.dump(5.5), 5.5)
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

    def test_decimal_field(self):
        field = DecimalField()

        self.assertEqual(field.format(1), '1')
        self.assertEqual(field.format(1.1), '1.1')
        self.assertEqual(field.format('1.1'), '1.1')
        self.assertEqual(field.format('nan'), 'NaN')
        self.assertEqual(field.format('inf'), 'Infinity')

        self.assertEqual(field.parse(1), Decimal('1'))
        self.assertEqual(field.parse(1.1), Decimal('1.1'))
        self.assertEqual(field.parse('1.1'), Decimal('1.1'))
        self.assertEqual(str(field.parse('nan')), 'NaN')
        self.assertEqual(str(field.parse('inf')), 'Infinity')

        field = DecimalField(dump_as=float, scale=2, rounding=ROUND_CEILING)
        self.assertEqual(field.format(1.1), 1.1)
        self.assertEqual(field.format(1), 1.0)
        self.assertEqual(field.format('inf'), float('inf'))
        self.assertEqual(field.format(1.111), 1.12)
        self.assertEqual(field.format(-1.111), -1.11)

        with self.assertRaises(TypeError):
            DecimalField(dump_as=1)

    def test_bool_field(self):
        field = BooleanField()

        # dump
        self.assertEqual(field.dump(True), True)
        self.assertEqual(field.dump(False), False)
        self.assertEqual(field.dump(None), None)

        # load
        self.assertEqual(field.load(None), None)
        self.assertEqual(field.load(True), True)
        self.assertEqual(field.load(False), False)
        self.assertEqual(field.load(0), False)
        self.assertEqual(field.load(1), True)
        self.assertEqual(field.load([]), False)
        self.assertEqual(field.load({}), False)
        self.assertEqual(field.load('True'), True)
        self.assertEqual(field.load('False'), False)
        self.assertEqual(field.load('y'), True)
        self.assertEqual(field.load('n'), False)
        self.assertEqual(field.load('1'), True)
        self.assertEqual(field.load('0'), False)
        self.assertEqual(field.load('xxx'), True)
        self.assertEqual(field.load(''), False)

    def test_list_field(self):
        field = ListField(item_field=FloatField())

        # dump
        self.assertListEqual(field.dump([1.0, 2.0, 3.0]), [1.0, 2.0, 3.0])
        self.assertListEqual(field.dump([]), [])
        self.assertEqual(field.dump(None), None)

        # load
        self.assertListEqual(field.load([1, 2, 3]), [1.0, 2.0, 3.0])
        self.assertListEqual(field.load([]), [])

        with self.assertRaises(ValidationError) as ctx:
            field.load([1, 'a', 3])
        result = ctx.exception.msg
        self.assertIsInstance(result.errors[1], ValueError)
        self.assertEqual(result.invalid_data[1], 'a')
        self.assertEqual(result.valid_data, [1.0, 3.0])

        with self.assertRaises(TypeError):
            field.load(1)
        self.assertIsNone(field.load(None))
        field.allow_none = False
        with self.assertRaises(ValidationError) as ctx:
            field.load(None)
        self.assertEqual(ctx.exception.msg, field.error_messages['none'])

        field = ListField(item_field=FloatField(), all_errors=False)
        with self.assertRaises(ValidationError) as ctx:
            field.load([1, 'a', 'b'])
        result = ctx.exception.msg
        self.assertEqual(set(result.errors), {1})
        self.assertEqual(result.invalid_data[1], 'a')
        self.assertEqual(result.valid_data, [1.0])

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
        self.base_test_datetime_field(dt, invalid_dt, DatetimeField, '%Y%m%d%H%M%S')
        self.base_test_datetime_field(dt.time(), invalid_dt.time(), TimeField, '%H%M%S')
        self.base_test_datetime_field(dt.date(), invalid_dt.date(), DateField, '%Y%m%d')

    def base_test_datetime_field(self, dt, invalid_dt, FieldClass, fmt):
        # dump
        field = FieldClass()
        dt_str = field.dump(dt)
        self.assertEqual(dt_str, dt.strftime(field.fmt))

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
        a_cata = ACatalyst()
        field = NestedField(a_cata, name='a', key='a')

        self.assertEqual(field.dump({'name': '1'}), {'name': '1'})
        self.assertEqual(field.dump({'name': '1234'}), {'name': '1234'})
        with self.assertRaises(ValidationError):
            field.dump({'n': 'm'})
        with self.assertRaises(ValidationError):
            field.dump(1)

        self.assertEqual(field.load({'name': '1'}), {'name': '1'})
        with self.assertRaises(ValidationError):
            field.load({'n': 'm'})
        with self.assertRaises(ValidationError):
            field.load({'name': '1234'})
        with self.assertRaises(ValidationError):
            field.load(1)

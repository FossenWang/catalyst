from unittest import TestCase
from datetime import datetime, time, date

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
        # dump to json
        self.assertEqual(a.fixed_value.dump_to_json('asd'), '1')

        # test load
        self.assertEqual(a.fixed_value.load(0), 1)
        self.assertRaises(TypeError, a.fixed_value.load, '0')
        self.assertRaises(AssertionError, a.fixed_value.load, -1)
        self.assertRaises(AssertionError, a.fixed_value.load, 100)

        # test validators
        self.assertEqual(len(a.fixed_value.validators), 2)
        self.assertRaises(TypeError, a.fixed_value.set_validators, 1)
        self.assertRaises(TypeError, a.fixed_value.add_validator, 1)

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
        # dump to json
        self.assertEqual(string_field.dump_to_json('xxx'), '"xxx"')
        self.assertEqual(string_field.dump_to_json('1'), '"1"')
        self.assertEqual(string_field.dump_to_json(None), 'null')

        # load
        self.assertEqual(string_field.load('xxx'), 'xxx')
        self.assertEqual(string_field.load(123), '123')
        self.assertEqual(string_field.load([1]), '[1]')
        self.assertRaises(ValidationError, string_field.load, '')
        self.assertRaises(ValidationError, string_field.load, None)

        string_field.allow_none = True
        self.assertEqual(string_field.load(None), None)

    def test_int_field(self):
        int_field = IntegerField(name='integer', key='integer', min_value=-10, max_value=100)

        # dump
        self.assertEqual(int_field.dump(1), 1)
        self.assertEqual(int_field.dump(1.6), 1)
        self.assertEqual(int_field.dump('10'), 10)
        # dump to json
        self.assertEqual(int_field.dump_to_json(1), '1')
        self.assertEqual(int_field.dump_to_json('1'), '1')
        self.assertEqual(int_field.dump_to_json(None), 'null')

        # load
        self.assertEqual(int_field.load(0), 0)
        self.assertEqual(int_field.load(1), 1)
        self.assertEqual(int_field.load('1'), 1)

        self.assertRaises(ValueError, int_field.load, '')
        self.assertRaises(ValidationError, int_field.load, 111)
        self.assertRaises(ValidationError, int_field.load, None)
        self.assertRaises(ValueError, int_field.load, 'asd')
        self.assertRaises(TypeError, int_field.load, [])

    def test_float_field(self):
        float_field = FloatField(name='float_', key='float', min_value=-11.1, max_value=111.1)

        # dump
        self.assertEqual(float_field.dump(1), 1.0)
        self.assertEqual(float_field.dump(0), 0.0)
        self.assertEqual(float_field.dump(5.5), 5.5)
        self.assertEqual(float_field.dump('10'), 10.0)
        self.assertEqual(float_field.dump(None), None)
        # dump to json
        self.assertEqual(float_field.dump_to_json(1), '1.0')
        self.assertEqual(float_field.dump_to_json('0'), '0.0')
        self.assertEqual(float_field.dump_to_json(None), 'null')

        # load
        self.assertEqual(float_field.load(0), 0.0)
        self.assertEqual(float_field.load('1.1'), 1.1)
        self.assertEqual(float_field.load(-11.1), -11.1)
        self.assertEqual(float_field.load(111.1), 111.1)
        self.assertEqual(float_field.load(11), 11)

        self.assertRaises(ValueError, float_field.load, '')
        self.assertRaises(ValidationError, float_field.load, 111.11)
        self.assertRaises(ValidationError, float_field.load, None)
        self.assertRaises(TypeError, float_field.load, [])

    def test_bool_field(self):
        bool_field = BoolField(name='bool_', key='bool')

        # dump
        self.assertEqual(bool_field.dump(True), True)
        self.assertEqual(bool_field.dump(False), False)
        self.assertEqual(bool_field.dump(None), None)
        # dump to json
        self.assertEqual(bool_field.dump_to_json(True), 'true')
        self.assertEqual(bool_field.dump_to_json(False), 'false')
        self.assertEqual(bool_field.dump_to_json(None), 'null')

        # load
        self.assertEqual(bool_field.load(True), True)
        self.assertEqual(bool_field.load(False), False)
        self.assertEqual(bool_field.load('False'), True)
        self.assertEqual(bool_field.load(0), False)
        self.assertEqual(bool_field.load(1), True)
        self.assertEqual(bool_field.load([]), False)

    def test_list_field(self):
        list_field = ListField(name='list_', key='list', item_field=FloatField(), required=True)

        # dump
        self.assertListEqual(list_field.dump([1, 2, 3]), [1.0, 2.0, 3.0])
        self.assertListEqual(list_field.dump([]), [])
        self.assertEqual(list_field.dump(None), None)
        with self.assertRaises(TypeError):
            list_field.dump(1)
        # dump to json
        self.assertEqual(list_field.dump_to_json([1, 2, 3]), '[1.0, 2.0, 3.0]')
        self.assertEqual(list_field.dump_to_json([]), '[]')
        self.assertEqual(list_field.dump_to_json(None), 'null')
        with self.assertRaises(TypeError):
            list_field.dump_to_json(1)

        # load
        self.assertListEqual(list_field.load([1, 2, 3]), [1.0, 2.0, 3.0])
        self.assertListEqual(list_field.load([]), [])

        with self.assertRaises(ValidationError) as c:
            list_field.load(1)
        self.assertEqual(c.exception.msg, list_field.error_messages['iterable'])

        with self.assertRaises(ValidationError) as c:
            list_field.load(None)
        self.assertEqual(c.exception.msg, list_field.error_messages['none'])
        list_field.allow_none = True
        self.assertIsNone(list_field.load(None))

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

        # dump to json
        self.assertEqual(callable_field.dump_to_json(test_func), '12')
        self.assertEqual(callable_field.dump_to_json(None), 'null')

    def test_datetime_field(self):
        def base_test(now, type_, FieldClass, fmt):
            # dump
            field = FieldClass(name='time', key='time')
            dt_str = field.dump(now)
            self.assertEqual(dt_str, now.strftime(field.default_fmt))

            field = FieldClass(name='time', key='time', fmt=fmt)
            dt_str = field.dump(now)
            self.assertEqual(dt_str, now.strftime(fmt))

            # dump to json
            self.assertEqual(field.dump_to_json(now), f'"{dt_str}"')
            self.assertEqual(field.dump_to_json(None), 'null')

            # load
            if type_ is datetime:
                dt = datetime.strptime(dt_str, fmt)
            elif type_ is time:
                dt = datetime.strptime(dt_str, fmt).time()
            elif type_ is date:
                dt = datetime.strptime(dt_str, fmt).date()
            self.assertEqual(field.load(dt_str), dt)
            self.assertRaises(ValueError, field.load, '2018Y')

        now = datetime.now()
        base_test(now, datetime, DatetimeField, '%Y%m%d%H%M%S')
        base_test(now.time(), time, TimeField, '%H%M%S')
        base_test(now.date(), date, DateField, '%Y%m%d')

    def test_nest_field(self):
        class A:
            def __init__(self, name):
                self.name = name

        class ACatalyst(Catalyst):
            name = StringField(max_length=3, required=True)
        a_cata = ACatalyst()
        field = NestedField(a_cata, name='a', key='a')

        self.assertEqual(field.dump(A('1')), {'name': '1'})
        self.assertEqual(field.dump_to_json(A('1')), '{"name": "1"}')
        self.assertEqual(field.load({'name': '1'}), {'name': '1'})
        self.assertRaises(ValidationError, field.load, {'n': 'm'})
        self.assertRaises(ValidationError, field.load, {'name': '1234'})
        self.assertRaises(TypeError, field.load, 1)

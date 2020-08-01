import math

from decimal import Decimal, ROUND_CEILING
from unittest import TestCase
from datetime import datetime, timedelta

from catalyst import Catalyst
from catalyst.fields import (
    BaseField, Field, StringField, IntegerField, FloatField,
    BooleanField, ListField, CallableField,
    DatetimeField, TimeField, DateField,
    NestedField, DecimalField, ConstantField,
    SeparatedField,
)
from catalyst.utils import no_processing
from catalyst.exceptions import ValidationError


class FieldTest(TestCase):
    def test_field_override_method(self):
        field = Field()

        field.override_method(no_processing, 'dump')
        self.assertEqual(field.dump, no_processing)
        self.assertEqual(field.dump(1), 1)

        field.override_method(attr='load')(no_processing)
        self.assertEqual(field.load, no_processing)
        self.assertEqual(field.load(1), 1)

        field = Field()
        @field.set_format
        def to_str_1(value):
            return str(value)
        self.assertEqual(field.format, to_str_1)
        self.assertEqual(field.format(1), '1')

        @field.set_format
        def to_str_2(value, field, original_method):
            assert isinstance(field, Field)
            return original_method(value)
        self.assertEqual(field.format, to_str_2)
        self.assertEqual(field.format(1), '1')

        field = Field()
        @field.set_format
        def to_str_3(self, value, field):
            assert self is field
            assert isinstance(self, Field)
            return str(value)
        self.assertEqual(field.format, to_str_3)
        self.assertEqual(field.format(1), '1')

        @field.set_format(obj_name='obj', original_name='old')
        def to_str_4(self, value, obj, old):
            assert self is obj
            assert isinstance(obj, Field)
            return old(value)
        self.assertEqual(field.format, to_str_4)
        self.assertEqual(field.format(1), '1')

        field = Field()
        @field.set_format
        def to_str_5(value, **kwargs):
            assert set(kwargs) == {'field', 'original_method'}
            return str(value)
        self.assertEqual(field.format, to_str_5)
        self.assertEqual(field.format(1), '1')

        @field.set_format(obj_name='obj', original_name='old')
        def to_str_6(value, **kwargs):
            assert set(kwargs) == {'obj', 'old'}
            return str(value)
        self.assertEqual(field.format, to_str_6)
        self.assertEqual(field.format(1), '1')

        with self.assertRaises(TypeError):
            field.set_format(lambda field, value: str(value))

    def test_field(self):
        field = BaseField()
        with self.assertRaises(NotImplementedError):
            field.load()
        with self.assertRaises(NotImplementedError):
            field.dump()

        # test set field opts in class
        class A:
            field = Field()

            @staticmethod
            @field.set_format
            def return_1(value):
                return 1

            @staticmethod
            @field.set_parse
            def field_add_1(value):
                return value + 1

            @staticmethod
            @field.set_validators
            def large_than(value):
                assert value > 0
                return value + 1  # useless return

            @staticmethod
            @field.add_validator
            def less_than(value):
                assert value < 100

        a = A()

        # test dump
        self.assertEqual(a.field.dump(1000), 1)
        self.assertEqual(a.field.dump('asd'), 1)

        # test load
        self.assertEqual(a.field.load(0), 1)
        with self.assertRaises(TypeError):
            a.field.load(None)
        with self.assertRaises(TypeError):
            a.field.load('asd')
        with self.assertRaises(AssertionError):
            a.field.load(-1)
        with self.assertRaises(AssertionError):
            a.field.load(100)

        # test validators
        self.assertEqual(len(a.field.validators), 2)

        # test wrong args
        with self.assertRaises(TypeError):
            a.field.set_validators(1)
        with self.assertRaises(TypeError):
            a.field.add_validator(1)
        with self.assertRaises(TypeError):
            a.field.set_format(1)
        with self.assertRaises(TypeError):
            a.field.set_parse(1)

        # test set functions when init field
        field = Field(
            formatter=A.return_1,
            parser=a.field.parse)
        self.assertEqual(field.format, A.return_1)
        self.assertEqual(field.parse, A.field_add_1)

        # test error msg
        field = Field(key='a', allow_none=False, error_messages={'none': '666'})
        with self.assertRaises(ValidationError) as cm:
            field.load(None)
        self.assertEqual(cm.exception.msg, '666')

        # test in and not in
        field = Field(in_='123', not_in='456')
        self.assertEqual(field.load('1'), '1')
        self.assertEqual(len(field.validators), 2)
        with self.assertRaises(ValidationError) as cm:
            field.load('0')
        with self.assertRaises(ValidationError) as cm:
            field.load('4')

    def test_string_field(self):
        field = StringField(
            name='string', key='string', min_length=2, max_length=12,
            error_messages={'not_between': 'Must >= {self.minimum}'})

        # dump
        self.assertEqual(field.dump('xxx'), 'xxx')
        self.assertEqual(field.dump(1), '1')
        self.assertEqual(field.dump([]), '[]')
        self.assertEqual(field.dump(None), None)

        # load
        self.assertEqual(field.load('xxx'), 'xxx')
        self.assertEqual(field.load(123), '123')
        self.assertEqual(field.load([1]), '[1]')
        self.assertEqual(field.load(None), None)
        with self.assertRaises(ValidationError) as cm:
            field.load('')

        # change validator's error message
        self.assertEqual(cm.exception.msg, 'Must >= 2')
        self.assertEqual(
            field.error_messages['not_between'],
            field.validators[0].error_messages['not_between'])

        field.allow_none = False
        with self.assertRaises(ValidationError):
            field.load(None)

        # match regex
        field = StringField(
            regex='a',
            error_messages={'no_match': 'not match "{self.regex.pattern}"'})
        self.assertEqual(field.load('a'), 'a')

        with self.assertRaises(ValidationError) as cm:
            field.load('')
        self.assertEqual(cm.exception.msg, 'not match "a"')

    def test_int_field(self):
        field = IntegerField(
            name='integer', key='integer', minimum=-10, maximum=100,
            error_messages={'not_between': '{self.maximum}'})

        # dump
        self.assertEqual(field.dump(1), 1)
        self.assertEqual(field.dump(1.6), 1)
        self.assertEqual(field.dump('10'), 10)

        # load
        self.assertEqual(field.load(0), 0)
        self.assertEqual(field.load(1), 1)
        self.assertEqual(field.load('1'), 1)
        self.assertEqual(field.load(None), None)

        with self.assertRaises(ValidationError) as cm:
            field.load(111)
        self.assertEqual(cm.exception.msg, '100')
        with self.assertRaises(ValueError):
            field.load('')
        with self.assertRaises(ValueError):
            field.load('asd')
        with self.assertRaises(TypeError):
            field.load([])

    def test_float_field(self):
        field = FloatField(minimum=-11.1, maximum=111.1)

        # dump
        self.assertEqual(field.dump(5.5), 5.5)
        self.assertEqual(field.dump(1), 1.0)
        self.assertEqual(field.dump(0), 0.0)
        self.assertEqual(field.dump('10'), 10.0)
        self.assertEqual(field.dump(None), None)
        self.assertTrue(math.isnan(field.dump('nan')))
        self.assertTrue(math.isinf(field.dump('inf')))

        # load
        self.assertEqual(field.load(0), 0.0)
        self.assertEqual(field.load('1.1'), 1.1)
        self.assertEqual(field.load(-11.1), -11.1)
        self.assertEqual(field.load(111.1), 111.1)
        self.assertEqual(field.load(11), 11)
        self.assertEqual(field.load(None), None)

        with self.assertRaises(ValueError):
            field.load('')
        with self.assertRaises(TypeError):
            field.load([])
        with self.assertRaises(ValidationError):
            field.load(111.11)
        with self.assertRaises(ValidationError):
            field.load('nan')

        # test nan & inf
        field = FloatField()
        self.assertTrue(math.isnan(field.dump('nan')))
        self.assertTrue(math.isinf(field.dump('inf')))
        self.assertTrue(math.isnan(field.load('nan')))
        self.assertTrue(math.isinf(field.load('inf')))

    def test_decimal_field(self):
        field = DecimalField()

        self.assertEqual(field.dump(1), '1')
        self.assertEqual(field.dump(1.1), '1.1')
        self.assertEqual(field.dump('1.1'), '1.1')
        self.assertEqual(field.dump('nan'), 'NaN')
        self.assertEqual(field.dump('inf'), 'Infinity')
        self.assertEqual(field.dump(None), None)

        self.assertEqual(field.load(1), Decimal('1'))
        self.assertEqual(field.load(1.1), Decimal('1.1'))
        self.assertEqual(field.load('1.1'), Decimal('1.1'))
        self.assertEqual(field.load(None), None)
        self.assertTrue(field.load('nan').is_nan())
        self.assertTrue(field.load('inf').is_infinite())

        field = DecimalField(dump_as=float, places=2, rounding=ROUND_CEILING)
        self.assertEqual(field.dump(1.1), 1.1)
        self.assertEqual(field.dump(1), 1.0)
        self.assertEqual(field.dump(1.111), 1.12)
        self.assertEqual(field.dump(-1.111), -1.11)
        self.assertTrue(math.isnan(field.dump('nan')))
        self.assertTrue(math.isinf(field.dump('inf')))
        self.assertEqual(field.dump(None), None)

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
        dt = datetime(2019, 11, 11, 11, 11, 11)
        invalid_dt = dt + timedelta(days=1, seconds=1)
        self.base_test_datetime_field(dt, invalid_dt, DatetimeField, '%Y%m%d%H%M%S')
        self.base_test_datetime_field(dt.time(), invalid_dt.time(), TimeField, '%H%M%S')
        self.base_test_datetime_field(dt.date(), invalid_dt.date(), DateField, '%Y%m%d')

    def base_test_datetime_field(self, dt, invalid_dt, FieldClass, fmt):
        # test dump
        field = FieldClass()
        dt_str = field.dump(dt)
        self.assertEqual(dt_str, dt.strftime(field.fmt))

        field = FieldClass(fmt=fmt)
        dt_str = field.dump(dt)
        self.assertEqual(dt_str, dt.strftime(fmt))

        self.assertEqual(field.dump(None), None)
        with self.assertRaises(TypeError):
            field.dump(1)

        # test load
        field = FieldClass(maximum=dt)
        dt_str = field.dump(dt)
        self.assertEqual(field.load(dt_str), dt)
        # `load_default` might be a datetime object
        self.assertEqual(field.load(dt), dt)
        self.assertEqual(field.load(None), None)

        with self.assertRaises(ValueError):
            field.load('2018Y')
        with self.assertRaises(ValidationError):
            field.load(invalid_dt)

    def test_list_field(self):
        with self.assertRaises(TypeError):
            ListField()

        with self.assertRaises(TypeError):
            field = ListField(FloatField)

        field = ListField(item_field=FloatField())

        # dump
        self.assertListEqual(field.dump([1.0, 2.0, 3.0]), [1.0, 2.0, 3.0])
        self.assertListEqual(field.dump([]), [])
        with self.assertRaises(TypeError):
            field.dump(1)
        with self.assertRaises(TypeError):
            field.dump(None)

        # load
        self.assertListEqual(field.load([1, 2, 3]), [1.0, 2.0, 3.0])
        self.assertListEqual(field.load([]), [])

        with self.assertRaises(ValidationError) as cm:
            field.load([1, 'a', 3])
        result = cm.exception.detail
        self.assertIsInstance(result.errors[1], ValueError)
        self.assertEqual(result.invalid_data[1], 'a')
        self.assertEqual(result.valid_data, [1.0, 3.0])

        with self.assertRaises(TypeError):
            field.load(1)
        with self.assertRaises(TypeError):
            field.load(None)

        field = ListField(item_field=FloatField(), all_errors=False)
        with self.assertRaises(ValidationError) as cm:
            field.load([1, 'a', 'b'])
        result = cm.exception.detail
        self.assertEqual(set(result.errors), {1})
        self.assertEqual(result.invalid_data[1], 'a')
        self.assertEqual(result.valid_data, [1.0])

        # two-dimensional array
        field = ListField(ListField(IntegerField()))

        data = [[1], [2]]
        self.assertListEqual(data, field.load(data))

        data = [[1], ['x']]
        with self.assertRaises(ValidationError) as cm:
            field.load(data)
        result = cm.exception.detail
        self.assertIsInstance(result.errors[1][0], ValueError)

        data = [[1], None]
        with self.assertRaises(ValidationError) as cm:
            field.load(data)
        result = cm.exception.detail
        self.assertIsInstance(result.errors[1], TypeError)

        # list with dict items
        field = ListField(NestedField(Catalyst({'x': IntegerField()})))

        data = [{'x': 1}, {'x': 2}]
        self.assertListEqual(data, field.load(data))

        data = [{'x': 1}, {'x': 'x'}]
        with self.assertRaises(ValidationError) as cm:
            field.load(data)
        result = cm.exception.detail
        self.assertIsInstance(result.errors[1]['x'], ValueError)

        data = [{'x': 1}, None]
        with self.assertRaises(ValidationError) as cm:
            field.load(data)
        result = cm.exception.detail
        self.assertIsInstance(result.errors[1]['load'], TypeError)

        field = ListField(IntegerField(), 2, 3)
        self.assertListEqual(field.load(['1', '2']), [1, 2])
        with self.assertRaises(ValidationError):
            field.load(['1'])
        with self.assertRaises(ValidationError):
            field.load(['1', '2', '3', '4'])

    def test_separated_field(self):
        field = SeparatedField(IntegerField())

        self.assertEqual(field.load('1 2 3'), [1, 2, 3])
        with self.assertRaises(ValidationError):
            field.load('1 a 3')

        self.assertEqual(field.dump([1, '2', 3]), '1 2 3')
        with self.assertRaises(ValidationError):
            field.dump([1, 'a', 3])

        field = SeparatedField(IntegerField(), separator=',')
        self.assertEqual(field.load('1,2,3'), [1, 2, 3])
        self.assertEqual(field.dump([1, '2', 3]), '1,2,3')

    def test_nest_field(self):
        with self.assertRaises(TypeError):
            NestedField()

        with self.assertRaises(TypeError):
            field = NestedField(Catalyst)

        fields = {'name': StringField(max_length=3)}
        field = NestedField(Catalyst(fields), name='a', key='a')

        self.assertEqual(field.dump({'name': '1'}), {'name': '1'})
        self.assertEqual(field.dump({'name': '1234'}), {'name': '1234'})
        with self.assertRaises(ValidationError):
            field.dump({'n': 'm'})
        with self.assertRaises(ValidationError):
            field.dump(1)

        self.assertEqual(field.load({'name': '1'}), {'name': '1'})
        self.assertDictEqual(field.load({'n': 'm'}), {})
        with self.assertRaises(ValidationError):
            field.load({'name': '1234'})
        with self.assertRaises(ValidationError):
            field.load(1)

        # list with dict items
        field = NestedField(Catalyst({'x': IntegerField()}), many=True)

        data = [{'x': 1}, {'x': 2}]
        self.assertListEqual(data, field.load(data))

        data = [{'x': 1}, {'x': 'x'}]
        with self.assertRaises(ValidationError) as cm:
            field.load(data)
        result = cm.exception.detail
        self.assertIsInstance(result.errors[1]['x'], ValueError)

        data = [{'x': 1}, None]
        with self.assertRaises(ValidationError) as cm:
            field.load(data)
        result = cm.exception.detail
        self.assertIsInstance(result.errors[1]['load'], TypeError)

    def test_constant_field(self):
        CONSTANT = 'x'
        field = ConstantField(CONSTANT)
        self.assertEqual(field.load(1), CONSTANT)
        self.assertEqual(field.dump(2), CONSTANT)

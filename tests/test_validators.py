import enum

from flask_fossen.testcases import FlaskTestCase
from flask_fossen.validators import generate_validators_from_mapper, column_validator_map, \
StringValidator, MaxLengthValidator, IntegerValidator, EnumValidator, \
PasswordValidator, EmailValidator

from flask_fossen.coltypes import Enum, PasswordType, EmailType

from .test_app.app.database import User


class ValidatorsTest(FlaskTestCase):
    def test_StringValidator(self):
        string_validator = StringValidator()
        self.assertEqual(string_validator('key', 'asd'),'asd')
        self.assertRaises(AssertionError, string_validator, 'key', 1)

    def test_MaxLengthValidator(self):
        maxLength_validator = MaxLengthValidator(3)
        self.assertEqual(maxLength_validator('key', 'asd'),'asd')
        self.assertRaises(AssertionError, maxLength_validator, 'key', 1)
        self.assertRaises(AssertionError, maxLength_validator, 'key', 'asdzxc')
        self.assertRaises(AssertionError, maxLength_validator, 'key', None)

    def test_IntegerValidator(self):
        integer_validator = IntegerValidator()
        self.assertEqual(integer_validator('key', 0), 0)
        self.assertEqual(integer_validator('key', 1), 1)
        self.assertEqual(integer_validator('key', '200'), 200)
        self.assertRaises(ValueError, integer_validator, 'key', 'any')
        self.assertRaises(TypeError, integer_validator, 'key', [])
        self.assertRaises(TypeError, integer_validator, 'key', None)

    def test_EnumValidator(self):
        class TestEnum(enum.Enum):
            qqq=1
            www=2
            eee=3
        enum_type = Enum(TestEnum)
        enum_validator = EnumValidator(enum_type._valid_lookup)
        self.assertEqual(enum_validator('key', 'qqq'), 'qqq')
        self.assertEqual(enum_validator('key', TestEnum(2)), 'www')
        self.assertRaises(LookupError, enum_validator, 'key', 3)

    def test_EmailValidator(self):
        email_validator = EmailValidator()
        self.assertEqual(email_validator('key', 'asd@123.com'), 'asd@123.com')
        self.assertEqual(email_validator('key', 'asd@123.com.cn'), 'asd@123.com.cn')
        self.assertRaises(AssertionError, email_validator, 'key', '@123.com')
        self.assertRaises(AssertionError, email_validator, 'key', 'asd@')
        self.assertRaises(AssertionError, email_validator, 'key', '123.com')
        self.assertRaises(AssertionError, email_validator, 'key', 'asd@com')
        self.assertRaises(AssertionError, email_validator, 'key', 'asd@.com')

    def test_PasswordValidator(self):
        password_validator = PasswordValidator(6,20, '_,./')
        self.assertEqual(password_validator('key', 'asd123'), 'asd123')
        self.assertEqual(password_validator('key', 'asd_,./123'), 'asd_,./123')
        self.assertRaises(AssertionError, password_validator, 'key', 'asd45')
        self.assertRaises(AssertionError, password_validator, 'key', 'asd456@')
        self.assertRaises(AssertionError, password_validator, 'key', '12345678')
        self.assertRaises(AssertionError, password_validator, 'key', 'qweasdzxc')

    def test_ValidatorMapper(self):
        validators, required = generate_validators_from_mapper(User.__mapper__)
        self.assertEqual(required, ['name', 'email'])
        self.assertIsInstance(validators['id'][0], IntegerValidator)
        self.assertIsInstance(validators['name'][0], MaxLengthValidator)
        self.assertIsInstance(validators['email'][0], MaxLengthValidator)


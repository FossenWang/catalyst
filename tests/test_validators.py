import enum

from flask_fossen.testcases import FlaskTestCase
from flask_fossen.validators import generate_validators_from_mapper, column_validator_map, \
MaxLengthValidator, IntegerValidator, EnumValidator, \
PasswordValidator, EmailValidator

from flask_fossen.coltypes import Enum, PasswordType, EmailType

from .test_app.app.database import User


class ValidatorsTest(FlaskTestCase):
    def test_MaxLengthValidator(self):
        maxLength_validator = MaxLengthValidator(3)
        self.assertEqual(maxLength_validator('asd'),'asd')
        self.assertRaises(AssertionError, maxLength_validator, 'asdzxc')

    def test_IntegerValidator(self):
        integer_validator = IntegerValidator()
        self.assertEqual(integer_validator(0), 0)
        self.assertEqual(integer_validator(1), 1)
        self.assertEqual(integer_validator('200'), 200)
        self.assertRaises(ValueError, integer_validator, 'any')
        self.assertRaises(TypeError, integer_validator, [])
        self.assertRaises(TypeError, integer_validator, None)

    def test_EnumValidator(self):
        class TestEnum(enum.Enum):
            qqq=1
            www=2
            eee=3
        enum_type = Enum(TestEnum)
        enum_validator = EnumValidator(enum_type._valid_lookup)
        self.assertEqual(enum_validator('qqq'), 'qqq')
        self.assertEqual(enum_validator(TestEnum(2)), 'www')
        self.assertRaises(LookupError, enum_validator, 3)

    def test_EmailValidator(self):
        email_validator = EmailValidator()
        self.assertEqual(email_validator('asd@123.com'), 'asd@123.com')
        self.assertEqual(email_validator('asd@123.com.cn'), 'asd@123.com.cn')
        self.assertRaises(AssertionError, email_validator, '@123.com')
        self.assertRaises(AssertionError, email_validator, 'asd@')
        self.assertRaises(AssertionError, email_validator, '123.com')
        self.assertRaises(AssertionError, email_validator, 'asd@com')
        self.assertRaises(AssertionError, email_validator, 'asd@.com')
        self.assertRaises(TypeError, email_validator, [])

    def test_PasswordValidator(self):
        password_validator = PasswordValidator(6,20, '_,./')
        self.assertEqual(password_validator('asd123'), 'asd123')
        self.assertEqual(password_validator('asd_,./123'), 'asd_,./123')
        self.assertRaises(AssertionError, password_validator, 'asd45')
        self.assertRaises(AssertionError, password_validator, 'asd456@')
        self.assertRaises(AssertionError, password_validator, '12345678')
        self.assertRaises(AssertionError, password_validator, 'qweasdzxc')

    def test_ValidatorMapper(self):
        validators, required = generate_validators_from_mapper(User.__mapper__)
        self.assertEqual(required, ['username', 'email'])
        self.assertIsInstance(validators['id'][0], IntegerValidator)
        self.assertIsInstance(validators['username'][0], MaxLengthValidator)
        self.assertIsInstance(validators['email'][0], EmailValidator)
        self.assertIsInstance(validators['password'][0], PasswordValidator)


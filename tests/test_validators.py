from flask_fossen.testcases import FlaskTestCase
from flask_fossen.validators import StringValidator, MaxLengthValidator, IntegerValidator, generate_validators_from_mapper

from .test_app.app import create_app, db
from .test_app.app.database import User, Article

class ValidatorsTest(FlaskTestCase):
    app = create_app()
    db = db

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

    def test_ValidatorMapper(self):
        _validators, required = generate_validators_from_mapper(User.__mapper__)
        print(required)
        for vld in _validators['id']:
            self.assertIsInstance(vld, IntegerValidator)
        for vld in _validators['name']:
            self.assertIsInstance(vld, MaxLengthValidator)
        for vld in _validators['email']:
            self.assertIsInstance(vld, MaxLengthValidator)


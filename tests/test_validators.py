from flask_fossen.testcases import FlaskTestCase
from flask_fossen.validators import *

# from .test_app.app import create_app, db

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

    def test_IntegerValidator(self):
        integer_validator = IntegerValidator()
        self.assertEqual(integer_validator('key', '200'), 200)
        self.assertRaises(ValueError, integer_validator, 'key', 'any')
        self.assertRaises(TypeError, integer_validator, 'key', [])



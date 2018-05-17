import re
from .coltypes import Integer, String, Boolean, EmailType, PasswordType


class StringValidator:
    def __call__(self, key, string):
        assert isinstance(string, str), "Enter a string, not %s" % type(string)
        return string


class MaxLengthValidator(StringValidator):
    def __init__(self, max_length):
        self.max_length = max_length
        self.message = "Ensure string length is less than or equal to %d" % max_length

    def __call__(self, key, string):
        super().__call__(key, string)
        assert len(string) <= self.max_length, self.message
        return string


class RegexValidator(StringValidator):
    def __init__(self):
        self.message = "Enter a valid value"
        self.regex = ''

    def __call__(self, key, value):
        super().__call__(key, value)
        assert re.match(self.regex, value), self.message
        return value


class EmailValidator(RegexValidator):
    def __init__(self):
        self.message = "Enter a valid email address"
        self.regex = r'^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$'


class PasswordValidator(StringValidator):
    def __init__(self, minlength, maxlength):
        self.minlength = minlength
        self.maxlength = maxlength

    def __call__(self, key, password):
        super().__call__(key, password)
        assert len(password) >= 6 and len(password)<=20, 'Password length must be greater than 6 and less than 20'
        have_number, have_letter, have_special= False, False, False
        for c in password:
            if c in '1234567890':
                have_number = True
            elif re.match('[a-z]', c):
                have_letter = True
            elif c in ',.?;_!@#$%^&*?':
                have_special = True
            else:
                assert False, 'Invalid char %s'%c
        assert have_number and have_letter, "Password must contain both number and letter"
        return password


class IntegerValidator:
    def __call__(self, key, value):
        return int(value)


class BooleanValidator:
    def __call__(self, key, value):
        assert isinstance(value, bool), "Enter True or False, not %s" % value
        return value


def get_string_validator(col):
    if col.type.length:
        return [MaxLengthValidator(col.type.length)]
    else:
        return [StringValidator()]

def get_email_validator(col):
    validators = [EmailValidator()]
    if col.type.length:
        validators.append(MaxLengthValidator(col.type.length))
    return validators

def get_password_validator(col):
    return [PasswordValidator()]

column_validator_map = {
    String: get_string_validator,
    Integer: lambda col: [IntegerValidator()],
    Boolean: lambda col: [BooleanValidator()],
    EmailType: get_email_validator,
    PasswordType: get_password_validator,
}

class ValidatorMapper:
    """
    Get model field definitions from the mapper
    and generate the corresponding validator.
    """
    def __call__(self, mapper):
        '''
        Return a tuple of two values.
        validator_map: mapping of model fields and validators list.
        required_fields: required fields list.
        '''
        validator_map = {}
        required_fields = []
        cols = mapper.columns
        rels = mapper.relationships
        for k, col in cols.items():
            k = col.name
            if not col.nullable and not col.primary_key:
                required_fields.append(k)
            get_validator = column_validator_map.get(type(col.type), lambda col: [])
            validator_map[k] = get_validator(col)
            
        # 关联字段的校验器
        for k, rel in rels.items():
            validator_map[k] = self.get_relationship_validator(rel)
        return validator_map, required_fields

    def get_relationship_validator(self, rel):
        return []


generate_validators_from_mapper = ValidatorMapper()


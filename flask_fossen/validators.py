import re
from .coltypes import Integer, String, Boolean, Enum, EmailType, PasswordType


class MaxLengthValidator:
    def __init__(self, max_length):
        self.max_length = max_length
        self.message = "Ensure string length is less than or equal to %d" % max_length

    def __call__(self,string):
        string = str(string)
        assert len(string) <= self.max_length, self.message
        return string


class RegexValidator:
    def __init__(self):
        self.message = "Enter a valid value"
        self.regex = ''

    def __call__(self, value):
        assert re.match(self.regex, value), self.message
        return value


class EmailValidator(RegexValidator):
    def __init__(self):
        self.message = "Enter a valid email address"
        self.regex = r'^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$'


class PasswordValidator:
    def __init__(self, minlength, maxlength, special_chars='_'):
        self.minlength = minlength
        self.maxlength = maxlength
        self.special_chars = special_chars

    def __call__(self, password):
        assert len(password) >= self.minlength and len(password)<=self.maxlength, \
        'Password length must be greater than %d and less than %d' \
        % (self.minlength, self.maxlength)

        have_number, have_letter = False, False
        for c in password:
            if c in '1234567890':
                have_number = True
            elif re.match('[a-zA-z]', c):
                have_letter = True
            elif c in self.special_chars:
                pass
            else:
                assert False, \
                'Invalid char "%s", password only contains numbers, letters or "%s"' \
                % (c, self.special_chars)
        assert have_number and have_letter, "Password must contain both number and letter"
        return password


class IntegerValidator:
    def __call__(self, value):
        return int(value)


class BooleanValidator:
    def __call__(self, value):
        assert isinstance(value, bool), "Enter True or False, not %s" % value
        return value


class EnumValidator:
    def __init__(self, valid_lookup):
        self.valid_lookup = valid_lookup

    def __call__(self, value):
        if value in self.valid_lookup:
            return self.valid_lookup[value]
        else:
            raise LookupError('"%s" is not among the defined enum values' % value)


def get_string_validator(col):
    if col.type.length:
        return [MaxLengthValidator(col.type.length)]
    else:
        return []

def get_email_validator(col):
    validators = [EmailValidator()]
    if col.type.length:
        validators.append(MaxLengthValidator(col.type.length))
    return validators


column_validator_map = {
    String: get_string_validator,
    EmailType: get_email_validator,
    Integer: lambda col: [IntegerValidator()],
    Boolean: lambda col: [BooleanValidator()],
    Enum: lambda col: [EnumValidator(col.type._valid_lookup)],
    PasswordType: lambda col: [PasswordValidator(
        *col.type.raw_password_length, col.type.special_chars)],
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
            validator_map[k] = self.get_column_validator(col)
            
        # 关联字段的校验器
        for k, rel in rels.items():
            validator_map[k] = self.get_relationship_validator(rel)

        return validator_map, required_fields

    def get_relationship_validator(self, rel):
        return []

    def get_column_validator(self, col):
        get_validator = column_validator_map.get(type(col.type), lambda col: [])
        return get_validator(col)


generate_validators_from_mapper = ValidatorMapper()


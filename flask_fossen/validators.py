import re
from sqlalchemy.sql.sqltypes import Integer, String, Boolean, Enum

from .coltypes import EmailType, PasswordType


class MaxLengthValidator:
    def __init__(self, max_length):
        self.max_length = max_length
        self.message = "Ensure string length is less than or equal to %d" % max_length

    def __call__(self, string):
        string = str(string)
        assert len(string) <= self.max_length, self.message
        return string


class RegexValidator:
    def __init__(self, regex='', message="Enter a valid value"):
        self.message = message
        self.regex = regex

    def __call__(self, value):
        assert re.match(self.regex, value), self.message
        return value
regex_validator = RegexValidator()


class EmailValidator(RegexValidator):
    def __init__(self):
        super().__init__(
            regex=r'^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$',
            message="Enter a valid email address"
        )
email_validator = EmailValidator()


class PasswordValidator:
    def __init__(self, minlength, maxlength, special_chars='_'):
        self.minlength = minlength
        self.maxlength = maxlength
        self.special_chars = special_chars

    def __call__(self, password):
        assert len(password) >= self.minlength and len(password) <= self.maxlength, \
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
integer_validator = IntegerValidator()


class BooleanValidator:
    def __call__(self, value):
        assert isinstance(
            value, bool) or value is None, "Enter None, True or False, not %s" % value
        return value
boolean_validator = BooleanValidator()


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
    validators = [email_validator]
    if col.type.length:
        validators.insert(0, MaxLengthValidator(col.type.length))
    return validators


column_validator_map = {
    String: get_string_validator,
    EmailType: get_email_validator,
    Integer: lambda col: [integer_validator],
    Boolean: lambda col: [boolean_validator],
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
            if not col.nullable and col.autoincrement != True and not col.default:
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


class ValidationResult:
    def __init__(self, valid_data, errors, invalid_data):
        self.valid_data = valid_data
        self.is_valid = not errors
        self.errors = errors
        self.invalid_data = invalid_data

    def __str__(self):
        return 'is valid: '+str(self.is_valid)


def _validate_data(cls, data):
    '''
    Validate data and collect the error information
    if valid return (True, errors), else return (False, errors)
    '''
    valid_data, errors, invalid_data = {}, {}, {}
    if not data:
        data = {}
    # ignore irrelevant data
    for name in cls._meta.default_validators:
        results = []
        value = data.get(name)
        if value is None:
            if name in cls._meta.required_fields:
                results.append('Ensure value is not None')
        else:
            valid_data[name] = value
            validators = cls._meta.default_validators.get(name)
            for validator in validators:
                try:
                    valid_data[name] = validator(valid_data[name])
                except Exception as e:
                    results.append(str(e))
        if results:
            errors[name] = results
            invalid_data[name] = value
    return ValidationResult(valid_data, errors, invalid_data)


class ValidatorSet:
    def __init__(self, validator_map, required_fields=None):
        self.default_validators = validator_map
        self.required_fields = required_fields if required_fields else []
        self._meta = type('Meta', (object,), {})
        self._meta.default_validators = validator_map
        self._meta.required_fields = self.required_fields
        self.validate_data = lambda data: _validate_data(self, data)

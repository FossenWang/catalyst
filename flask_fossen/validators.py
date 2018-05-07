from sqlalchemy.sql.sqltypes import Integer, String


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


class IntegerValidator:
    def __call__(self, key, value):
        return int(value)


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
            if not col.nullable and not col.primary_key:
                required_fields.append(k)
            get_validator = self.column_validator_map.get(type(col.type))
            if get_validator:
                validator_map[k] = get_validator(self, col)
            else:
                validator_map[k] = []
        # 关联字段的校验器
        for k, rel in rels.items():
            validator_map[k] = self.get_relationship_validator(rel)
        return validator_map, required_fields

    def get_string_validator(self, col):
        if col.type.length:
            return [MaxLengthValidator(col.type.length)]
        else:
            return [StringValidator()]

    def get_integer_validator(self, col):
        return [IntegerValidator()]

    def get_relationship_validator(self, rel):
        return []

    column_validator_map = {
        String: get_string_validator,
        Integer: get_integer_validator,
    }

generate_validators_from_mapper = ValidatorMapper()


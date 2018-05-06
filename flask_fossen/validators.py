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
    从mapper中读取模型字段定义，生成相应的校验器
    返回两个参数
    属性和校验器列表的字典 validator_map = {'id': [integer_validator, ...], ...}
    必填属性列表 required_fields
    """
    def __call__(self, mapper):
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


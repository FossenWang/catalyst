from typing import Dict

from .fields import *
from .validators import *


class CatalystMeta(type):
    def __new__(cls, name, bases, attrs):
        # collect fields
        fields = {}  # type: Dict[Field]
        for key, value in attrs.items():
            if isinstance(value, Field):
                if value.name is None:
                    value.name = key
                if value.key is None:
                    value.key = key
                fields[key] = value
        attrs['_fields'] = fields
        new_cls = type.__new__(cls, name, bases, attrs)
        return new_cls


class Catalyst(metaclass=CatalystMeta):
    _fields = None  # type: Dict[Field]

    def __init__(self, raise_error=False):
        self.raise_error = raise_error

    def serialize(self, obj) -> dict:
        obj_dict = {}
        for field in self._fields.values():
            obj_dict[field.key] = field.serialize(obj)
        return obj_dict

    def deserialize(self, data: dict) -> dict:
        invalid_data = {}
        valid_data = {}
        errors = {}
        for field in self._fields.values():
            try:
                value = field.deserialize(data)
            except Exception as e:
                errors[field.key] = e
                if field.key in data:
                    # 无效数据的应该返回原始数据，忽略原始数据中没有的字段
                    invalid_data[field.key] = data[field.key]
            else:
                if field.key in data:
                    # 有效数据返回处理后的数据，忽略原始数据中没有的字段
                    valid_data[field.key] = value

        validation_result = ValidationResult(valid_data, errors, invalid_data)
        if not validation_result.is_valid and self.raise_error:
            raise ValidationError(validation_result)
        return validation_result

from pprint import pprint

from .fields import *
from .validators import *


class CatalystMeta(type):
    def __new__(cls, name, bases, attrs):
        # collect fields
        fields = {}
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
    _fields = None

    def __init__(self, raise_error=False):
        self.raise_error = raise_error

    def serialize(self, obj):
        obj_dict = {}
        for field in self._fields.values():
            obj_dict[field.key] = field.serialize(obj)
        return obj_dict

    def deserialize(self, data):
        invalid_data = {}
        valid_data = {}
        errors = {}
        for field in self._fields.values():
            try:
                if field.key not in data:
                    # ignore or raise exception
                    if field.required:
                        raise ValidationError("Key '%s' is required" % field.key)
                    continue
                else:
                    value = data[field.key]
            except Exception as e:
                errors[field.key] = e
                continue

            try:
                value = field.deserialize(value)
            except Exception as e:
                errors[field.key] = e
                invalid_data[field.key] = value
            else:
                valid_data[field.key] = value

        validation_result = ValidationResult(valid_data, errors, invalid_data)
        if not validation_result.is_valid and self.raise_error:
            raise ValidationError(validation_result)
        return validation_result

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
    def __init__(self):
        pass

    def extract(self, obj):
        obj_dict = {}
        for field in self._fields.values():
            # key和name的默认值需要用别的办法设置
            obj_dict[field.key] = field.extract(obj)
        return obj_dict

    def validate(self, data):
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
                value = field.validate(value)
            except Exception as e:
                errors[field.key] = e
                invalid_data[field.key] = value
            else:
                valid_data[field.key] = value
        return ValidationResult(valid_data, errors, invalid_data)




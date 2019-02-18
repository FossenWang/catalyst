from typing import Dict, Iterable, Callable
from collections.abc import Mapping

from .fields import Field
from .validators import ValidationError


FieldDict = Dict[str, Field]


class LoadResult(dict):
    def __init__(self, valid_data: dict = None, errors: dict = None, invalid_data: dict = None):
        self.valid_data = valid_data if valid_data else {}
        super().__init__(valid_data)
        self.is_valid = not errors
        self.errors = errors if errors else {}
        self.invalid_data = invalid_data if invalid_data else {}

    def __repr__(self):
        if not self.is_valid:
            return 'LoadResult(is_valid=%s, errors=%s)' % (self.is_valid, self.strferrors())
        return 'LoadResult(is_valid=%s, valid_data=%s)' % (self.is_valid, super().__repr__())

    def __str__(self):
        if not self.is_valid:
            return str(self.strferrors())
        return super().__repr__()

    def strferrors(self):
        return {k: str(self.errors[k]) for k in self.errors}


class CatalystMeta(type):
    def __new__(cls, name, bases, attrs):
        # collect fields
        fields = {}  # type: FieldDict
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
    _fields = {}  # type: FieldDict

    def __init__(self, fields: Iterable[str] = None, dump_fields: Iterable[str] = None,
                 load_fields: Iterable[str] = None, raise_error: bool = False):
        if not fields:
            fields = self._fields.keys()
        if not dump_fields:
            dump_fields = fields
        if not load_fields:
            load_fields = fields

        self._dump_fields = self._copy_fields(
            self._fields, dump_fields,
            lambda k: not self._fields[k].no_dump)

        self._load_fields = self._copy_fields(
            self._fields, load_fields,
            lambda k: not self._fields[k].no_load)

        self.raise_error = raise_error

    def _copy_fields(self, fields: FieldDict, keys: Iterable[str],
                     is_copying: Callable[[str], bool])-> FieldDict:
        new_fields = {}  # type: FieldDict
        for key in keys:
            if is_copying(key):
                new_fields[key] = fields[key]
        return new_fields

    def dump(self, obj) -> dict:
        obj_dict = {}
        for field in self._dump_fields.values():
            obj_dict[field.key] = field.dump(obj)
        return obj_dict

    def load(self, data: dict) -> LoadResult:
        if not isinstance(data, Mapping):
            raise TypeError('Argment data must be a mapping object.')

        invalid_data = {}
        valid_data = {}
        errors = {}
        for field in self._load_fields.values():
            try:
                value = field.load(data)
            except Exception as e:
                errors[field.key] = e
                if field.key in data:
                    # 无效数据的应该返回原始数据，忽略原始数据中没有的字段
                    invalid_data[field.key] = data[field.key]
            else:
                if field.key in data:
                    # 有效数据返回处理后的数据，忽略原始数据中没有的字段
                    valid_data[field.key] = value

        load_result = LoadResult(valid_data, errors, invalid_data)
        if not load_result.is_valid and self.raise_error:
            raise ValidationError(load_result)
        return load_result

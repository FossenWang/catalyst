from typing import Dict, Iterable, Callable, Mapping

from .fields import Field
from .exceptions import ValidationError


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
        # collect fields to cls._field_dict
        fields = {}  # type: FieldDict
        for key, value in attrs.items():
            if isinstance(value, Field):
                if value.name is None:
                    value.name = key
                if value.key is None:
                    value.key = key
                fields[key] = value
        attrs['_field_dict'] = fields
        new_cls = type.__new__(cls, name, bases, attrs)
        return new_cls


def get_attr_or_item(obj, name):
    if hasattr(obj, name):
        return getattr(obj, name)

    if isinstance(obj, Mapping) and name in obj:
        return obj.get(name)

    raise AttributeError(f'{obj} has no attribute or key "{name}".')


class Catalyst(metaclass=CatalystMeta):
    _field_dict = {}  # type: FieldDict

    from_attribute = 0
    from_dict_key = 1
    from_attribute_or_key = 2
    _getter_map = {
        from_attribute: getattr,
        from_dict_key: lambda d, key: d[key],
        from_attribute_or_key: get_attr_or_item,
    }

    def __init__(self, fields: Iterable[str] = None, dump_fields: Iterable[str] = None,
                 load_fields: Iterable[str] = None, raise_error: bool = False, 
                 dump_from: int = from_attribute_or_key):
        if not fields:
            fields = set(self._field_dict.keys())
        if not dump_fields:
            dump_fields = fields
        if not load_fields:
            load_fields = fields

        self._dump_field_dict = self._copy_fields(
            self._field_dict, dump_fields,
            lambda k: not self._field_dict[k].no_dump)

        self._load_field_dict = self._copy_fields(
            self._field_dict, load_fields,
            lambda k: not self._field_dict[k].no_load)

        self.raise_error = raise_error

        self.set_dump_getter(dump_from)

    def _copy_fields(self, fields: FieldDict, keys: Iterable[str],
                     is_copying: Callable[[str], bool]) -> FieldDict:
        new_fields = {}  # type: FieldDict
        for key in keys:
            if is_copying(key):
                new_fields[key] = fields[key]
        return new_fields

    def set_dump_getter(self, dump_from: int):
        'Set once when initialize.'
        if dump_from not in self._getter_map:
            raise ValueError((
                'Invalid value for "dump_from" which should '
                f'be one of {tuple(self._getter_map)}.'))
        self.get_dump_value = self._getter_map.get(dump_from)

    def dump(self, obj) -> dict:
        obj_dict = {}
        for field in self._dump_field_dict.values():
            value = self.get_dump_value(obj, field.name)
            obj_dict[field.key] = field.dump(value)
        return obj_dict

    def load(self, data: dict) -> LoadResult:
        if not isinstance(data, Mapping):
            raise TypeError('Argment data must be a mapping object.')

        invalid_data = {}
        valid_data = {}
        errors = {}
        for field in self._load_field_dict.values():
            try:
                raw_value = self.get_load_value(data, field)
                value = field.load(raw_value)
            except Exception as e:
                errors[field.key] = e
                if field.key in data:
                    # 无效数据的应该返回原始数据，忽略原始数据中没有的字段
                    invalid_data[field.key] = raw_value
            else:
                if field.key in data:
                    # 有效数据返回处理后的数据，忽略原始数据中没有的字段
                    valid_data[field.key] = value

        load_result = LoadResult(valid_data, errors, invalid_data)
        if not load_result.is_valid and self.raise_error:
            raise ValidationError(load_result)
        return load_result

    def get_load_value(self, data: dict, field: Field):
        if field.key in data:
            value = data[field.key]
            return value
        if field.required:
            raise ValidationError(field.error_messages.get('required'))
        return None

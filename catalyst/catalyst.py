import json

from typing import Dict, Iterable, Callable, Mapping, Any

from .fields import Field
from .exceptions import ValidationError
from .utils import dump_from_attribute_or_key, no_default


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
            return 'LoadResult(is_valid=%s, errors=%s)' % (self.is_valid, self.format_errors())
        return 'LoadResult(is_valid=%s, valid_data=%s)' % (self.is_valid, super().__repr__())

    def __str__(self):
        if not self.is_valid:
            return str(self.format_errors())
        return super().__repr__()

    def format_errors(self):
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


class Catalyst(metaclass=CatalystMeta):
    _field_dict = {}  # type: FieldDict

    def __init__(self, fields: Iterable[str] = None, dump_fields: Iterable[str] = None,
                 load_fields: Iterable[str] = None, raise_error: bool = False,
                 dump_from: Callable[[Any, str], Any] = None):
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

        if not dump_from:
            dump_from = dump_from_attribute_or_key
        self.set_dump_from(dump_from)

    def _copy_fields(self, fields: FieldDict, keys: Iterable[str],
                     is_copying: Callable[[str], bool]) -> FieldDict:
        new_fields = {}  # type: FieldDict
        for key in keys:
            if is_copying(key):
                new_fields[key] = fields[key]
        return new_fields

    def set_dump_from(self, dump_from: Callable[[Any, str], Any]):
        if not isinstance(dump_from, Callable):
            raise TypeError('Param `dump_from` must be Callable.')
        self.dump_from = dump_from

    def dump(self, obj) -> dict:
        obj_dict = {}
        for field in self._dump_field_dict.values():
            value = self.get_dump_value(obj, field)
            obj_dict[field.key] = field.dump(value)
        return obj_dict

    def get_dump_value(self, obj, field: Field):
        try:
            value = self.dump_from(obj, field.name)
        except (AttributeError, KeyError) as e:
            if field.dump_default is no_default:
                raise e
            value = field.dump_default
        return value

    def dump_to_json(self, obj) -> str:
        return json.dumps(self.dump(obj))

    def load(self, data: dict, raise_error: bool = None) -> LoadResult:
        if not isinstance(data, Mapping):
            raise TypeError('Param `data` must be a mapping object.')

        invalid_data = {}
        valid_data = {}
        errors = {}
        for field in self._load_field_dict.values():
            try:
                raw_value = self.get_load_value(data, field)
            except Exception as e:
                errors[field.key] = e
                continue

            try:
                value = field.load(raw_value)
            except Exception as e:
                errors[field.key] = e
                invalid_data[field.key] = raw_value
            else:
                valid_data[field.key] = value

        load_result = LoadResult(valid_data, errors, invalid_data)
        if raise_error is None:
            raise_error = self.raise_error
        if not load_result.is_valid and raise_error:
            raise ValidationError(load_result)
        return load_result

    def load_from_json(self, s: str, raise_error: bool = None) -> LoadResult:
        return self.load(json.loads(s), raise_error=raise_error)

    def get_load_value(self, data: dict, field: Field):
        try:
            value = data[field.key]
        except KeyError as e:
            if field.required:
                raise ValidationError(field.error_messages.get('required'))
            if field.load_default is no_default:
                raise e
            value = field.load_default
        return value

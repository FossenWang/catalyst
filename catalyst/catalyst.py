import json

from typing import Dict, Iterable, Callable, Mapping, Any
from types import MappingProxyType

from .fields import Field, NestedField
from .exceptions import ValidationError
from .utils import dump_from_attribute_or_key, missing


FieldDict = Dict[str, Field]


class LoadResult(dict):
    def __init__(self, valid_data: dict = None, errors: dict = None, invalid_data: dict = None):
        super().__init__(valid_data if valid_data else {})
        self.valid_data = MappingProxyType(self)
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


class BaseCatalyst:
    _field_dict = {}  # type: FieldDict

    def __init__(self,
                 fields: Iterable[str] = None,
                 dump_fields: Iterable[str] = None,
                 load_fields: Iterable[str] = None,
                 raise_error: bool = False,
                 collect_errors: bool = True,
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
        self.collect_errors = collect_errors

        if not dump_from:
            dump_from = dump_from_attribute_or_key
        if not callable(dump_from):
            raise TypeError('Argument "dump_from" must be Callable.')
        self.dump_from = dump_from

    def _copy_fields(self, fields: FieldDict, keys: Iterable[str],
                     is_copying: Callable[[str], bool]) -> FieldDict:
        new_fields = {}  # type: FieldDict
        for key in keys:
            if is_copying(key):
                new_fields[key] = fields[key]
        return new_fields

    def dump(self, obj) -> dict:
        obj = self.pre_dump(obj)

        result = {}
        for field in self._dump_field_dict.values():
            try:
                value = self.dump_from(obj, field.name)
            except (AttributeError, KeyError) as e:
                default = field.dump_default
                if default is missing:
                    if field.dump_required:
                        # raise error when field is missing and required
                        raise e
                    # ignore missing field not required
                    continue
                # set default value for missing field
                value = default() if callable(default) else default
            result[field.key] = field.dump(value)

        result = self.post_dump(result)
        return result

    def dump_to_json(self, obj) -> str:
        return json.dumps(self.dump(obj))

    def pre_dump(self, obj):
        return obj

    def post_dump(self, result: dict) -> dict:
        return result

    def load(self,
             data: dict,
             raise_error: bool = None,
             collect_errors: bool = None
             ) -> LoadResult:

        if not isinstance(data, Mapping):
            raise TypeError('Argument "data" must be a mapping object.')

        if raise_error is None:
            raise_error = self.raise_error
        if collect_errors is None:
            collect_errors = self.collect_errors

        errors = {}

        try:
            data = self.pre_load(data)
        except Exception as e:
            if not collect_errors:
                raise e
            error_key = getattr(self.pre_load, 'error_key', 'pre_load')
            errors[error_key] = e

        invalid_data = {}
        valid_data = {}
        if not errors:
            for field in self._load_field_dict.values():
                try:
                    default = field.load_default
                    if callable(default):
                        default = default()
                    raw_value = data.get(field.key, default)
                    if raw_value is missing:
                        if field.load_required:
                            # raise error when field is missing and required
                            field.error('required')
                        # ignore missing field not required
                        continue
                    # set default value for missing field
                    value = field.load(raw_value)
                except Exception as e:
                    if not collect_errors:
                        raise e
                    errors[field.key] = e
                    if raw_value is not missing:
                        invalid_data[field.key] = raw_value
                else:
                    valid_data[field.key] = value

        if not errors:
            try:
                valid_data = self.post_load(valid_data)
            except Exception as e:
                if not collect_errors:
                    raise e
                error_key = getattr(self.post_load, 'error_key', 'post_load')
                errors[error_key] = e

        load_result = LoadResult(valid_data, errors, invalid_data)
        if not load_result.is_valid and raise_error:
            raise ValidationError(load_result)
        return load_result

    def load_from_json(self,
                       s: str,
                       raise_error: bool = None,
                       collect_errors: bool = None
                       ) -> LoadResult:
        return self.load(
            json.loads(s), raise_error=raise_error,
            collect_errors=collect_errors)

    def pre_load(self, data: dict) -> dict:
        return data
    pre_load.error_key = 'pre_load'

    def post_load(self, data: dict) -> dict:
        return data
    post_load.error_key = 'post_load'


class CatalystMeta(type):
    def __new__(cls, name, bases, attrs):
        # collect fields to cls._field_dict
        fields = {}  # type: FieldDict
        for key, value in attrs.items():
            if isinstance(value, cls):
                value = value()

            if isinstance(value, BaseCatalyst):
                value = NestedField(value)
                attrs[key] = value

            if isinstance(value, Field):
                if value.name is None:
                    value.name = key
                if value.key is None:
                    value.key = key
                fields[key] = value

        attrs['_field_dict'] = fields
        new_cls = type.__new__(cls, name, bases, attrs)
        return new_cls


class Catalyst(BaseCatalyst, metaclass=CatalystMeta):
    __doc__ = BaseCatalyst.__doc__

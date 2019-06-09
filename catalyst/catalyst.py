import json
import inspect

from typing import Dict, Iterable, Callable, Mapping, Sequence, Any
from functools import wraps, partial
from collections import OrderedDict

from .packer import CatalystPacker
from .fields import Field, NestedField, no_processing
from .exceptions import ValidationError
from .utils import dump_from_attribute_or_key, missing, \
    ensure_staticmethod, LoadResult


FieldDict = Dict[str, Field]


class BaseCatalyst:
    _field_dict = {}  # type: FieldDict
    __format_key__ = staticmethod(no_processing)
    __format_name__ = staticmethod(no_processing)

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

    def pre_dump(self, obj):
        return obj

    def post_dump(self, result: dict) -> dict:
        return result

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

    def dump_many(self, objs: Sequence) -> list:
        return [self.dump(obj) for obj in objs]

    def dump_to_json(self, obj) -> str:
        return json.dumps(self.dump(obj))

    def dump_args(self, func: Callable) -> Callable:
        """Decorator for dumping args by catalyst before function is called.
        The wrapper function takes args as same as args of the raw function.
        If args are invalid, error will be raised.
        In general, `*args` should be handled by ListField,
        and `**kwargs` should be handled by NestedField.
        """
        sig = inspect.signature(func)
        @wraps(func)
        def wrapper(*args, **kwargs):
            ba = sig.bind(*args, **kwargs)
            result = self.dump(ba.arguments)
            ba.arguments.update(result)
            return func(*ba.args, **ba.kwargs)
        return wrapper

    def dump_kwargs(self, func: Callable) -> Callable:
        """Decorator for dumping kwargs by catalyst before function is called.
        The wrapper function only takes kwargs, and unpacks dumping result to
        the raw function. If kwargs are invalid, error will be raised.
        """
        @wraps(func)
        def wrapper(**kwargs):
            kwargs = self.dump(kwargs)
            return func(**kwargs)
        return wrapper

    def pre_load(self, data: dict) -> dict:
        return data
    pre_load.error_key = 'pre_load'

    def post_load(self, data: dict) -> dict:
        return data
    post_load.error_key = 'post_load'

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
                    valid_data[field.name] = value

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

    def load_many(self,
                  data: Sequence,
                  raise_error: bool = None,
                  collect_errors: bool = None
                  ) -> LoadResult:
        if raise_error is None:
            raise_error = self.raise_error
        if collect_errors is None:
            collect_errors = self.collect_errors

        valid_data, errors, invalid_data = [], OrderedDict(), OrderedDict()
        for i, item in enumerate(data):
            result = self.load(item, False, collect_errors)
            valid_data.append(result.valid_data)
            if not result.is_valid:
                errors[i] = result.errors
                invalid_data[i] = result.invalid_data

        results = LoadResult(valid_data, errors, invalid_data)
        if raise_error:
            raise ValidationError(results)
        return results

    def load_from_json(self,
                       s: str,
                       raise_error: bool = None,
                       collect_errors: bool = None
                       ) -> LoadResult:
        return self.load(
            json.loads(s), raise_error=raise_error,
            collect_errors=collect_errors)

    def load_args(self,
                  func: Callable = None,
                  collect_errors: bool = None
                  ) -> Callable:
        """Decorator for loading args by catalyst before function is called.
        The wrapper function takes args as same as args of the raw function.
        If args are invalid, error will be raised.
        In general, `*args` should be handled by ListField,
        and `**kwargs` should be handled by NestedField.
        """
        if func:
            sig = inspect.signature(func)
            @wraps(func)
            def wrapper(*args, **kwargs):
                ba = sig.bind(*args, **kwargs)
                result = self.load(ba.arguments, raise_error=True, collect_errors=collect_errors)
                ba.arguments.update(result.valid_data)
                return func(*ba.args, **ba.kwargs)
            return wrapper

        return partial(self.load_args, collect_errors=collect_errors)

    def load_kwargs(self,
                    func: Callable = None,
                    collect_errors: bool = None
                    ) -> Callable:
        """Decorator for loading kwargs by catalyst before function is called.
        The wrapper function only takes kwargs, and unpacks loading result to
        the raw function. If kwargs are invalid, error will be raised.
        """
        if func:
            @wraps(func)
            def wrapper(**kwargs):
                result = self.load(kwargs, raise_error=True, collect_errors=collect_errors)
                return func(**result.valid_data)
            return wrapper

        return partial(self.load_kwargs, collect_errors=collect_errors)

    def pack(self, data):
        packer = CatalystPacker()
        return packer.pack(self, data)


class CatalystMeta(type):
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)

        new_cls.__format_name__ = ensure_staticmethod(new_cls.__format_name__)
        new_cls.__format_key__ = ensure_staticmethod(new_cls.__format_key__)
        format_name = new_cls.__format_name__
        format_key = new_cls.__format_key__

        # collect fields to cls._field_dict
        fields = {}  # type: FieldDict
        for attr in dir(new_cls):
            value = getattr(new_cls, attr)
            # init calalyst object
            if isinstance(value, cls):
                value = value()
            # wrap catalyst object as NestedField
            if isinstance(value, BaseCatalyst):
                value = NestedField(value)
                setattr(new_cls, attr, value)
            # automatic generate field name or key
            if isinstance(value, Field):
                if value.name is None:
                    value.name = format_name(attr)
                if value.key is None:
                    value.key = format_key(attr)
                fields[attr] = value

        new_cls._field_dict = fields
        return new_cls


class Catalyst(BaseCatalyst, metaclass=CatalystMeta):
    __doc__ = BaseCatalyst.__doc__

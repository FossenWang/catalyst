import inspect

from typing import Dict, Iterable, Callable, Sequence, Any
from functools import wraps, partial
from collections import OrderedDict

from .packer import CatalystPacker
from .fields import Field, NestedField
from .exceptions import ValidationError
from .utils import (
    missing, get_attr_or_item, get_item,
    LoadResult, DumpResult, Result, OptionBox
)


FieldDict = Dict[str, Field]


class BaseCatalyst:
    _field_dict = {}  # type: FieldDict

    class Options(OptionBox):
        dump_from = staticmethod(get_attr_or_item)
        dump_raise_error = False
        dump_all_errors = True
        dump_method = 'format'

        load_from = staticmethod(get_item)
        load_raise_error = False
        load_all_errors = True
        load_method = 'load'

    def __init__(self,
                 fields: Iterable[str] = None,
                 dump_fields: Iterable[str] = None,
                 dump_from: Callable[[Any, str], Any] = None,
                 dump_raise_error: bool = None,
                 dump_all_errors: bool = None,
                 dump_method: str = None,
                 load_fields: Iterable[str] = None,
                 load_from: Callable[[Any, str], Any] = None,
                 load_raise_error: bool = None,
                 load_all_errors: bool = None,
                 load_method: str = None,
                 ):
        if not fields:
            fields = set(self._field_dict.keys())
        if not dump_fields:
            dump_fields = fields
        if not load_fields:
            load_fields = fields

        self._dump_field_dict = self._copy_fields(
            self._field_dict, dump_fields,
            lambda k: not self._field_dict[k].opts.no_dump)

        self._load_field_dict = self._copy_fields(
            self._field_dict, load_fields,
            lambda k: not self._field_dict[k].opts.no_load)

        self.opts = self.Options(
            dump_from=dump_from,
            dump_raise_error=dump_raise_error,
            dump_all_errors=dump_all_errors,
            dump_method=dump_method,
            load_from=load_from,
            load_raise_error=load_raise_error,
            load_all_errors=load_all_errors,
            load_method=load_method,
        )

        if not callable(self.opts.dump_from):
            raise TypeError('"dump_from" must be Callable.')

        if not callable(self.opts.load_from):
            raise TypeError('"load_from" must be Callable.')

    @staticmethod
    def _copy_fields(fields: FieldDict, keys: Iterable[str],
                     is_copying: Callable[[str], bool]) -> FieldDict:
        new_fields = {}  # type: FieldDict
        for key in keys:
            if is_copying(key):
                new_fields[key] = fields[key]
        return new_fields

    @staticmethod
    def _format_field_key(key):
        return key

    @staticmethod
    def _format_field_name(name):
        return name

    def _side_effect(self, data, errors, name, raise_error):
        handle = getattr(self, name)
        try:
            data = handle(data)
        except Exception as e:
            if raise_error:
                raise e
            error_key = getattr(handle, 'error_key', name)
            errors[error_key] = e
        return data, errors

    def _base_handle(self,
                     data,
                     name: str,
                     raise_error: bool = None,
                     all_errors: bool = None,
                     method: str = None,
                     ) -> Result:
        if name == 'dump':
            source_attr = 'name'
            target_attr = 'key'
            ResultClass = DumpResult
            field_dict = self._dump_field_dict
            get_value = self.opts.dump_from
            raise_error = self.opts.get(dump_raise_error=raise_error)
            all_errors = self.opts.get(dump_all_errors=all_errors)
            method = self.opts.get(dump_method=method)
            if method not in {'dump', 'format', 'validate'}:
                raise ValueError("Argment 'method' must be in ('dump', 'format', 'validate').")
        elif name == 'load':
            source_attr = 'key'
            target_attr = 'name'
            ResultClass = LoadResult
            field_dict = self._load_field_dict
            get_value = self.opts.load_from
            raise_error = self.opts.get(load_raise_error=raise_error)
            all_errors = self.opts.get(load_all_errors=all_errors)
            method = self.opts.get(load_method=method)
            if method not in {'load', 'parse', 'validate'}:
                raise ValueError("Argment 'method' must be in ('load', 'parse', 'validate').")
        else:
            raise ValueError("Argment 'name' must be 'dump' or 'load'.")

        data, errors = self._side_effect(
            data, {}, f'pre_{name}', not all_errors)

        valid_data, invalid_data = {}, {}

        if not errors:
            for field in field_dict.values():
                default = getattr(field, f'{name}_default')
                required = getattr(field.opts, f'{name}_required')
                source = getattr(field, source_attr)
                target = getattr(field, target_attr)
                raw_value = missing

                raw_value = get_value(data, source, default)
                try:
                    # if the field's value is missing
                    # raise error if required otherwise skip
                    if raw_value is missing:
                        if required:
                            field.error('required')
                        continue

                    valid_data[target] = getattr(field, method)(raw_value)
                except Exception as e:
                    # collect errors and invalid data
                    errors[source] = e
                    if raw_value is not missing:
                        invalid_data[source] = raw_value
                    if not all_errors:
                        break

        if not errors:
            data, errors = self._side_effect(
                data, errors, f'post_{name}', not all_errors)

        result = ResultClass(valid_data, errors, invalid_data)
        if errors and raise_error:
            raise ValidationError(result)
        return result

    def dump(self,
             data,
             raise_error: bool = None,
             all_errors: bool = None,
             method: str = None,
             ) -> DumpResult:
        return self._base_handle(data, 'dump', raise_error, all_errors, method)

    def dump_many(self,
                  data: Sequence,
                  raise_error: bool = None,
                  all_errors: bool = None
                  ) -> DumpResult:
        raise_error = self.opts.get(dump_raise_error=raise_error)
        all_errors = self.opts.get(dump_all_errors=all_errors)

        valid_data, errors, invalid_data = [], OrderedDict(), OrderedDict()
        for i, item in enumerate(data):
            result = self.dump(item, False, all_errors)
            valid_data.append(result.valid_data)
            if not result.is_valid:
                errors[i] = result.errors
                invalid_data[i] = result.invalid_data

        results = DumpResult(valid_data, errors, invalid_data)
        if raise_error:
            raise ValidationError(results)
        return results

    def dump_args(self,
                  func: Callable,
                  all_errors: bool = None
                  ) -> Callable:
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
            result = self.dump(ba.arguments, True, all_errors)
            ba.arguments.update(result.valid_data)
            return func(*ba.args, **ba.kwargs)
        return wrapper

    def load(self,
             data,
             raise_error: bool = None,
             all_errors: bool = None,
             method: str = None,
             ) -> LoadResult:
        return self._base_handle(data, 'load', raise_error, all_errors, method)

    def load_many(self,
                  data: Sequence,
                  raise_error: bool = None,
                  all_errors: bool = None
                  ) -> LoadResult:
        raise_error = self.opts.get(load_raise_error=raise_error)
        all_errors = self.opts.get(load_all_errors=all_errors)

        valid_data, errors, invalid_data = [], OrderedDict(), OrderedDict()
        for i, item in enumerate(data):
            result = self.load(item, False, all_errors)
            valid_data.append(result.valid_data)
            if not result.is_valid:
                errors[i] = result.errors
                invalid_data[i] = result.invalid_data
                if not all_errors:
                    break

        results = LoadResult(valid_data, errors, invalid_data)
        if errors and raise_error:
            raise ValidationError(results)
        return results

    def load_args(self,
                  func: Callable = None,
                  all_errors: bool = None
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
                result = self.load(ba.arguments, True, all_errors)
                ba.arguments.update(result.valid_data)
                return func(*ba.args, **ba.kwargs)
            return wrapper

        return partial(self.load_args, all_errors=all_errors)

    def pre_dump(self, data):
        return data
    pre_dump.error_key = 'pre_dump'

    def post_dump(self, data):
        return data
    post_dump.error_key = 'post_dump'

    def pre_load(self, data):
        return data
    pre_load.error_key = 'pre_load'

    def post_load(self, data):
        return data
    post_load.error_key = 'post_load'

    def pack(self, data) -> CatalystPacker:
        packer = CatalystPacker()
        return packer.pack(self, data)


class CatalystMeta(type):
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)

        # collect fields to cls._field_dict
        fields = {}  # type: FieldDict
        for attr, value in attrs.items():
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
                    value.name = new_cls._format_field_name(attr)
                if value.key is None:
                    value.key = new_cls._format_field_key(attr)
                fields[attr] = value

        # inherit fields
        fields.update(new_cls._field_dict)
        new_cls._field_dict = fields
        return new_cls


class Catalyst(BaseCatalyst, metaclass=CatalystMeta):
    __doc__ = BaseCatalyst.__doc__

import inspect

from typing import Dict, Iterable, Callable, Sequence, Any
from functools import wraps, partial
from collections import OrderedDict

from .packer import CatalystPacker
from .fields import Field, NestedField
from .exceptions import ValidationError
from .utils import (
    missing, get_attr_or_item, get_item,
    LoadResult, DumpResult, CatalystResult, OptionBox
)


FieldDict = Dict[str, Field]


class BaseCatalyst:
    _field_dict = {}  # type: FieldDict

    class Options(OptionBox):
        dump_from = staticmethod(get_attr_or_item)
        dump_method = 'format'

        load_from = staticmethod(get_item)
        load_method = 'load'

        raise_error = False
        all_errors = True

    @staticmethod
    def _format_field_key(key):
        return key

    @staticmethod
    def _format_field_name(name):
        return name

    @staticmethod
    def _copy_fields(fields: FieldDict, keys: Iterable[str],
                     is_copying: Callable[[str], bool]) -> FieldDict:
        new_fields = {}  # type: FieldDict
        for key in keys:
            if is_copying(key):
                new_fields[key] = fields[key]
        return new_fields

    def __init__(self,
                 fields: Iterable[str] = None,
                 raise_error: bool = None,
                 all_errors: bool = None,
                 dump_fields: Iterable[str] = None,
                 dump_from: Callable[[Any, str], Any] = None,
                 dump_method: str = None,
                 load_fields: Iterable[str] = None,
                 load_from: Callable[[Any, str], Any] = None,
                 load_method: str = None,
                 **kwargs,
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
            raise_error=raise_error,
            all_errors=all_errors,
            dump_from=dump_from,
            dump_method=dump_method,
            load_from=load_from,
            load_method=load_method,
            **kwargs,
        )

        if not callable(self.opts.dump_from):
            raise TypeError("Argument `dump_from` must be Callable.")

        if not callable(self.opts.load_from):
            raise TypeError("Argument `load_from` must be Callable.")

        if self.opts.dump_method not in {'dump', 'format', 'validate'}:
            raise ValueError("Argument `method` must be in ('dump', 'format', 'validate').")

        if self.opts.load_method not in {'load', 'parse', 'validate'}:
            raise ValueError("Argument `method` must be in ('load', 'parse', 'validate').")

    def _side_effect(self, data, errors, name):
        handle = getattr(self, name)
        try:
            data = handle(data)
        except Exception as e:
            error_key = getattr(handle, 'error_key', name)
            errors[error_key] = e
        return data, errors

    def _base_handle(self,
                     name: str,
                     data: Any,
                     raise_error: bool = None,
                     all_errors: bool = None,
                     ) -> CatalystResult:
        if name == 'dump':
            source_attr = 'name'
            target_attr = 'key'
            ResultClass = DumpResult
            field_dict = self._dump_field_dict
            get_value = self.opts.dump_from
            method = self.opts.dump_method
        elif name == 'load':
            source_attr = 'key'
            target_attr = 'name'
            ResultClass = LoadResult
            field_dict = self._load_field_dict
            get_value = self.opts.load_from
            method = self.opts.load_method
        else:
            raise ValueError("Argument `name` must be 'dump' or 'load'.")
        raise_error = self.opts.get(raise_error=raise_error)
        all_errors = self.opts.get(all_errors=all_errors)

        data, errors = self._side_effect(data, {}, f'pre_{name}')

        valid_data, invalid_data = {}, {}

        if not errors:
            for field in field_dict.values():
                required = getattr(field.opts, f'{name}_required')
                default = getattr(field, f'{name}_default')
                source = getattr(field, source_attr)
                target = getattr(field, target_attr)

                raw_value = get_value(data, source, default)
                try:
                    # if the field's value is missing
                    # raise error if required otherwise skip
                    if raw_value is missing:
                        if required:
                            errors[source] = field.get_error('required')
                            if not all_errors:
                                break
                        continue

                    valid_data[target] = getattr(field, method)(raw_value)
                except Exception as e:
                    # collect errors and invalid data
                    if isinstance(e, ValidationError) and isinstance(e.msg, CatalystResult):
                        # distribute nested errors
                        valid_data[target] = e.msg.valid_data
                        errors[source] = e.msg.errors
                        invalid_data[source] = e.msg.invalid_data
                    else:
                        errors[source] = e
                        invalid_data[source] = raw_value
                    if not all_errors:
                        break

        if not errors:
            data, errors = self._side_effect(data, errors, f'post_{name}')

        result = ResultClass(valid_data, errors, invalid_data)
        if errors and raise_error:
            raise ValidationError(result)
        return result

    def _handle_many(self,
                     name: str,
                     data: Sequence,
                     raise_error: bool = None,
                     all_errors: bool = None,
                     ) -> CatalystResult:
        if name == 'dump':
            ResultClass = DumpResult
        elif name == 'load':
            ResultClass = LoadResult
        else:
            raise ValueError("Argument `name` must be 'dump' or 'load'.")
        raise_error = self.opts.get(raise_error=raise_error)
        all_errors = self.opts.get(all_errors=all_errors)

        valid_data, errors, invalid_data = [], OrderedDict(), OrderedDict()
        for i, item in enumerate(data):
            result = self._base_handle(name, item, False, all_errors)
            valid_data.append(result.valid_data)
            if not result.is_valid:
                errors[i] = result.errors
                invalid_data[i] = result.invalid_data
                if not all_errors:
                    break

        results = ResultClass(valid_data, errors, invalid_data)
        if raise_error:
            raise ValidationError(results)
        return results

    def _handle_args(self,
                     func: Callable = None,
                     name: str = None,
                     all_errors: bool = None,
                     ) -> Callable:
        """Decorator for handling args by catalyst before function is called.
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
                result = self._base_handle(name, ba.arguments, True, all_errors)
                ba.arguments.update(result.valid_data)
                return func(*ba.args, **ba.kwargs)
            return wrapper
        return partial(self._handle_args, name=name, all_errors=all_errors)

    def dump(self,
             data,
             raise_error: bool = None,
             all_errors: bool = None,
             ) -> DumpResult:
        return self._base_handle('dump', data, raise_error, all_errors)

    def dump_many(self,
                  data: Sequence,
                  raise_error: bool = None,
                  all_errors: bool = None,
                  ) -> DumpResult:
        return self._handle_many('dump', data, raise_error, all_errors)

    def dump_args(self,
                  func: Callable = None,
                  all_errors: bool = None,
                  ) -> Callable:
        return self._handle_args(func, 'load', all_errors)

    def load(self,
             data,
             raise_error: bool = None,
             all_errors: bool = None,
             ) -> LoadResult:
        return self._base_handle('load', data, raise_error, all_errors)

    def load_many(self,
                  data: Sequence,
                  raise_error: bool = None,
                  all_errors: bool = None,
                  ) -> LoadResult:
        return self._handle_many('load', data, raise_error, all_errors)

    def load_args(self,
                  func: Callable = None,
                  all_errors: bool = None,
                  ) -> Callable:
        return self._handle_args(func, 'load', all_errors)

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

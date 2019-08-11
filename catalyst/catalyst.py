import inspect

from typing import Dict, Iterable, Callable, Sequence, Any
from functools import wraps, partial
from collections import OrderedDict

from .packer import CatalystPacker
from .fields import Field, NestedField
from .exceptions import ValidationError
from .utils import missing, \
    get_attr_or_item, get_item, \
    LoadResult, DumpResult


FieldDict = Dict[str, Field]


class OptionBox:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if value is not None:
                setattr(self, key, value)

    def get(self, **kwargs):
        if len(kwargs) != 1:
            raise ValueError('只能填一个参数')
        for key, value in kwargs.items():
            if value is None:
                return getattr(self, key)
            return value


class BaseCatalyst:
    _field_dict = {}  # type: FieldDict

    class Options(OptionBox):
        dump_from = staticmethod(get_attr_or_item)
        dump_raise_error = False
        dump_all_errors = True
        dump_no_validate = True

        load_from = staticmethod(get_item)
        load_raise_error = False
        load_all_errors = True
        load_no_validate = False

    def __init__(self,
                 fields: Iterable[str] = None,
                 dump_fields: Iterable[str] = None,
                 dump_from: Callable[[Any, str], Any] = None,
                 dump_raise_error: bool = None,
                 dump_all_errors: bool = None,
                 dump_no_validate: bool = None,
                 load_fields: Iterable[str] = None,
                 load_from: Callable[[Any, str], Any] = None,
                 load_raise_error: bool = None,
                 load_all_errors: bool = None,
                 load_no_validate: bool = None,
                 ):
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

        self.opts = self.Options(
            dump_from=dump_from,
            dump_raise_error=dump_raise_error,
            dump_all_errors=dump_all_errors,
            dump_no_validate=dump_no_validate,
            load_from=load_from,
            load_raise_error=load_raise_error,
            load_all_errors=load_all_errors,
            load_no_validate=load_no_validate,
        )

        if not callable(self.opts.dump_from):
            raise TypeError('"dump_from" must be Callable.')

        if not callable(self.opts.load_from):
            raise TypeError('"load_from" must be Callable.')

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

    def pack(self, data) -> CatalystPacker:
        packer = CatalystPacker()
        return packer.pack(self, data)

    def dump(self,
             data,
             raise_error: bool = None,
             all_errors: bool = None,
             no_validate: bool = None,
             ) -> DumpResult:
        raise_error = self.opts.get(dump_raise_error=raise_error)
        all_errors = self.opts.get(dump_all_errors=all_errors)
        no_validate = self.opts.get(dump_no_validate=no_validate)

        data, errors = self._side_effect(
            data, {}, 'pre_dump', not all_errors)

        valid_data, invalid_data = {}, {}

        if not errors:
            method = 'format' if no_validate else 'dump'
            for field in self._dump_field_dict.values():
                raw_value = missing
                raw_value = self.opts.dump_from(data, field.name, field.dump_default)
                try:
                    # if the field's value is missing
                    # raise error if required otherwise skip
                    if raw_value is missing:
                        if field.dump_required:
                            field.error('required')
                        continue

                    valid_data[field.key] = getattr(field, method)(raw_value)
                except Exception as e:
                    # collect errors and invalid data
                    errors[field.name] = e
                    if raw_value is not missing:
                        invalid_data[field.name] = raw_value
                    if not all_errors:
                        break

        if not errors:
            data, errors = self._side_effect(
                data, errors, 'post_dump', not all_errors)

        dump_result = DumpResult(valid_data, errors, invalid_data)
        if errors and raise_error:
            raise ValidationError(dump_result)
        return dump_result

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

    def dump_kwargs(self,
                    func: Callable = None,
                    all_errors: bool = None
                    ) -> Callable:
        """Decorator for dumping kwargs by catalyst before function is called.
        The wrapper function only takes kwargs, and unpacks dumping result to
        the raw function. If kwargs are invalid, error will be raised.
        """
        if func:
            @wraps(func)
            def wrapper(**kwargs):
                result = self.dump(kwargs, True, all_errors)
                return func(**result.valid_data)
            return wrapper

        return partial(self.dump_kwargs, all_errors=all_errors)

    def load(self,
             data,
             raise_error: bool = None,
             all_errors: bool = None,
             no_validate: bool = None,
             ) -> LoadResult:
        raise_error = self.opts.get(load_raise_error=raise_error)
        all_errors = self.opts.get(load_all_errors=all_errors)
        no_validate = self.opts.get(load_no_validate=no_validate)

        data, errors = self._side_effect(
            data, {}, 'pre_load', not all_errors)

        valid_data, invalid_data = {}, {}

        if not errors:
            method = 'parse' if no_validate else 'load'
            for field in self._load_field_dict.values():
                raw_value = missing
                raw_value = self.opts.load_from(data, field.key, field.load_default)
                try:
                    # if the field's value is missing
                    # raise error if required otherwise skip
                    if raw_value is missing:
                        if field.load_required:
                            field.error('required')
                        continue

                    valid_data[field.name] = getattr(field, method)(raw_value)
                except Exception as e:
                    # collect errors and invalid data
                    errors[field.key] = e
                    if raw_value is not missing:
                        invalid_data[field.key] = raw_value
                    if not all_errors:
                        break

        if not errors:
            data, errors = self._side_effect(
                data, errors, 'post_load', not all_errors)

        load_result = LoadResult(valid_data, errors, invalid_data)
        if errors and raise_error:
            raise ValidationError(load_result)
        return load_result

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

    def load_kwargs(self,
                    func: Callable = None,
                    all_errors: bool = None
                    ) -> Callable:
        """Decorator for loading kwargs by catalyst before function is called.
        The wrapper function only takes kwargs, and unpacks loading result to
        the raw function. If kwargs are invalid, error will be raised.
        """
        if func:
            @wraps(func)
            def wrapper(**kwargs):
                result = self.load(kwargs, True, all_errors)
                return func(**result.valid_data)
            return wrapper

        return partial(self.load_kwargs, all_errors=all_errors)

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

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


class BaseCatalyst:
    _field_dict = {}  # type: FieldDict
    default_dump_from = staticmethod(get_attr_or_item)
    default_load_from = staticmethod(get_item)

    def __init__(self,
                 fields: Iterable[str] = None,
                 dump_fields: Iterable[str] = None,
                 dump_from: Callable[[Any, str], Any] = None,
                 dump_raise_error: bool = False,
                 dump_collect_errors: bool = True,
                 dump_skip_validation: bool = False,
                 load_fields: Iterable[str] = None,
                 load_from: Callable[[Any, str], Any] = None,
                 load_raise_error: bool = False,
                 load_collect_errors: bool = True,
                 load_skip_validation: bool = False,
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

        self.dump_raise_error = dump_raise_error
        self.dump_collect_errors = dump_collect_errors
        self.dump_skip_validation = dump_skip_validation
        self.load_raise_error = load_raise_error
        self.load_collect_errors = load_collect_errors
        self.load_skip_validation = load_skip_validation

        if not dump_from:
            dump_from = self.default_dump_from
        if not callable(dump_from):
            raise TypeError('"dump_from" must be Callable.')
        if not load_from:
            load_from = self.default_load_from
        if not callable(load_from):
            raise TypeError('"load_from" must be Callable.')
        self.dump_from = dump_from
        self.load_from = load_from

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

    def pack(self, data):
        packer = CatalystPacker()
        return packer.pack(self, data)

    def dump(self,
             data,
             raise_error: bool = None,
             collect_errors: bool = None,
             skip_validation: bool = None,
             ) -> DumpResult:

        if raise_error is None:
            raise_error = self.dump_raise_error
        if collect_errors is None:
            collect_errors = self.dump_collect_errors
        if skip_validation is None:
            skip_validation = self.dump_skip_validation

        data, errors = self._side_effect(
            data, {}, 'pre_dump', not collect_errors)

        valid_data, invalid_data = {}, {}

        if not errors:
            dump_method = 'format' if skip_validation else 'dump'
            for field in self._dump_field_dict.values():
                raw_value = missing
                raw_value = self.dump_from(data, field.name, field.dump_default)
                try:
                    # if the field's value is missing
                    # raise error if required otherwise skip
                    if raw_value is missing:
                        if field.dump_required:
                            field.error('required')
                        continue

                    value = getattr(field, dump_method)(raw_value)
                except Exception as e:
                    if not collect_errors:
                        raise e
                    # collect errors and invalid data
                    errors[field.name] = e
                    if raw_value is not missing:
                        invalid_data[field.name] = raw_value
                else:
                    valid_data[field.key] = value

        if not errors:
            data, errors = self._side_effect(
                data, errors, 'post_dump', not collect_errors)

        dump_result = DumpResult(valid_data, errors, invalid_data)
        if errors and raise_error:
            raise ValidationError(dump_result)
        return dump_result

    def dump_many(self,
                  data: Sequence,
                  raise_error: bool = None,
                  collect_errors: bool = None
                  ) -> DumpResult:
        if raise_error is None:
            raise_error = self.dump_raise_error
        if collect_errors is None:
            collect_errors = self.dump_collect_errors

        valid_data, errors, invalid_data = [], OrderedDict(), OrderedDict()
        for i, item in enumerate(data):
            result = self.dump(item, False, collect_errors)
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
                  collect_errors: bool = None
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
            result = self.dump(ba.arguments, True, collect_errors)
            ba.arguments.update(result.valid_data)
            return func(*ba.args, **ba.kwargs)
        return wrapper

    def dump_kwargs(self,
                    func: Callable = None,
                    collect_errors: bool = None
                    ) -> Callable:
        """Decorator for dumping kwargs by catalyst before function is called.
        The wrapper function only takes kwargs, and unpacks dumping result to
        the raw function. If kwargs are invalid, error will be raised.
        """
        if func:
            @wraps(func)
            def wrapper(**kwargs):
                result = self.dump(kwargs, True, collect_errors)
                return func(**result.valid_data)
            return wrapper

        return partial(self.dump_kwargs, collect_errors=collect_errors)

    def load(self,
             data: dict,
             raise_error: bool = None,
             collect_errors: bool = None,
             skip_validation: bool = None,
             ) -> LoadResult:

        if raise_error is None:
            raise_error = self.load_raise_error
        if collect_errors is None:
            collect_errors = self.load_collect_errors
        if skip_validation is None:
            skip_validation = self.dump_skip_validation

        data, errors = self._side_effect(
            data, {}, 'pre_load', not collect_errors)

        valid_data, invalid_data = {}, {}

        if not errors:
            method = 'parse' if skip_validation else 'load'
            for field in self._load_field_dict.values():
                raw_value = missing
                raw_value = self.load_from(data, field.key, field.load_default)
                try:
                    # if the field's value is missing
                    # raise error if required otherwise skip
                    if raw_value is missing:
                        if field.load_required:
                            field.error('required')
                        continue

                    value = getattr(field, method)(raw_value)
                except Exception as e:
                    if not collect_errors:
                        raise e
                    # collect errors and invalid data
                    errors[field.key] = e
                    if raw_value is not missing:
                        invalid_data[field.key] = raw_value
                else:
                    valid_data[field.name] = value

        if not errors:
            data, errors = self._side_effect(
                data, errors, 'post_load', not collect_errors)

        load_result = LoadResult(valid_data, errors, invalid_data)
        if errors and raise_error:
            raise ValidationError(load_result)
        return load_result

    def load_many(self,
                  data: Sequence,
                  raise_error: bool = None,
                  collect_errors: bool = None
                  ) -> LoadResult:
        if raise_error is None:
            raise_error = self.dump_raise_error
        if collect_errors is None:
            collect_errors = self.dump_collect_errors

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
                result = self.load(ba.arguments, True, collect_errors)
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
                result = self.load(kwargs, True, collect_errors)
                return func(**result.valid_data)
            return wrapper

        return partial(self.load_kwargs, collect_errors=collect_errors)

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

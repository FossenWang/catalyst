"""Catalyst class and its metaclass."""

import inspect

from typing import Dict, Iterable, Callable, Sequence, Any, Mapping
from functools import wraps, partial

from .base import CatalystABC
from .fields import Field, NestedField
from .exceptions import ValidationError, ExceptionType
from .utils import (
    missing, assign_attr_or_item_getter, assign_item_getter,
    LoadResult, DumpResult, BaseResult, bind_attrs, no_processing
)


FieldDict = Dict[str, Field]


class CatalystMeta(type):
    """Metaclass for `Catalyst` class. Binds fields to `_field_dict` attribute."""

    def __new__(cls, name, bases, attrs):
        new_cls = super().__new__(cls, name, bases, attrs)
        new_cls._set_fields(new_cls, attrs)
        return new_cls


class Catalyst(CatalystABC, metaclass=CatalystMeta):
    """Base Catalyst class for converting complex datatypes to and from
    native Python datatypes.

    Some instantiation params can set default values by class variables.
    The available params are `schema`, `dump_method`, `load_method`,
    `raise_error`, `all_errors`, `except_exception` and `process_aliases`.

    :param schema: A dict or instance or class which contains fields. This
        is a convenient way to avoid name clashes when fields are Python
        keywords or conflict with other attributes.
    :param dump_method: The method name of `Field`. The method is used to
        handle each field value when dumping data.
        Available values are 'dump', 'format' and 'validate'.
    :param load_method: Similar to `dump_method`.
        Available values are 'load', 'parse' and 'validate'.
    :param raise_error: Whether to raise error if error occurs when
        processing data. Errors are collected into a error dict, which key
        is field name, index of item of iterable or process name.
    :param all_errors: Whether to collect every errors of data and
        errors of process.
    :param except_exception: Which types of errors should be collected
        into process result. Usage is the same as `try/except` statement.
    :param process_aliases: A dict which key is process name, and value
        is process alias. When the process goes wrong, if its process name
        is in `process_aliases` dcit, the process alias will be a key
        in error dict with a value whict is the error.
        Available process names are 'pre_dump', 'dump', 'post_dump',
        'pre_dump_many', 'dump_many', 'post_dump_many', 'load', etc.
    :param include: The fields to include in both dump and load fields.
        If None, all fields are used.
        If `dump_include` or `load_include` is passed, `include` will
        not be used for dump or load fields.
    :param exclude: The fields to exclude from both dump and load fields.
        If a field appears in both `include` and `exclude`, it is not used.
        If `dump_exclude` or `load_exclude` is passed, `exclude` will
        not be used for dump or load fields.
        The fields filtering works like set operation, for example:
            used_fields = original_fields & include - exclude
        `Field.no_dump` and `Field.no_load` are also used to filter fields.
    :param dump_include: The fields to include in dump fields.
    :param dump_exclude: The fields to exclude from dump fields.
    :param load_include: The fields to include in load fields.
    :param load_exclude: The fields to exclude from dump fields.
    """
    schema: Any = None
    dump_method = 'format'
    load_method = 'load'
    raise_error = False
    all_errors = True
    except_exception: ExceptionType = Exception
    process_aliases = {}

    _field_dict: FieldDict = {}

    # assign getter for dumping & loading
    _assign_dump_getter = staticmethod(assign_attr_or_item_getter)
    _assign_load_getter = staticmethod(assign_item_getter)

    # generate field name and key and custom naming style
    _format_field_key = staticmethod(no_processing)
    _format_field_name = staticmethod(no_processing)

    def __init__(
            self,
            schema: Any = None,
            dump_method: str = None,
            load_method: str = None,
            raise_error: bool = None,
            all_errors: bool = None,
            except_exception: ExceptionType = None,
            process_aliases: Mapping[str, str] = None,
            include: Iterable[str] = None,
            exclude: Iterable[str] = None,
            dump_include: Iterable[str] = None,
            dump_exclude: Iterable[str] = None,
            load_include: Iterable[str] = None,
            load_exclude: Iterable[str] = None,
            **kwargs):
        bind_attrs(
            self,
            schema=schema,
            dump_method=dump_method,
            load_method=load_method,
            raise_error=raise_error,
            all_errors=all_errors,
            process_aliases=process_aliases,
            except_exception=except_exception,
            **kwargs,
        )

        if self.dump_method not in {'dump', 'format', 'validate'}:
            raise ValueError(
                "Attribute `dump_method` must be in ('dump', 'format', 'validate').")
        if self.load_method not in {'load', 'parse', 'validate'}:
            raise ValueError(
                "Attribute `load_method` must be in ('load', 'parse', 'validate').")

        # set fields from a dict or instance or class
        schema = self.schema
        if schema:
            if isinstance(schema, Mapping):
                attrs = schema
            else:
                attrs = {name: getattr(schema, name) for name in dir(schema)}
            self._set_fields(self, attrs)

        # include fields
        if include is None:
            include = self._field_dict.keys()
        if dump_include is None:
            dump_include = include
        if load_include is None:
            load_include = include

        # exclude fields
        exclude = set() if exclude is None else set(exclude)
        dump_exclude = exclude if dump_exclude is None else set(dump_exclude)
        load_exclude = exclude if load_exclude is None else set(load_exclude)
        if dump_exclude:
            dump_include = (field for field in dump_include if field not in dump_exclude)
        if load_exclude:
            load_include = (field for field in load_include if field not in load_exclude)

        try:
            self._dump_field_dict = self._copy_fields(
                self._field_dict, dump_include,
                lambda key: not self._field_dict[key].no_dump)
            self._load_field_dict = self._copy_fields(
                self._field_dict, load_include,
                lambda key: not self._field_dict[key].no_load)
        except KeyError as error:
            raise ValueError(f"Field '{error.args[0]}' does not exist.") from error

        # make processors when initializing for shorter run time
        self._do_dump = self._make_processor('dump', False)
        self._do_load = self._make_processor('load', False)
        self._do_dump_many = self._make_processor('dump', True)
        self._do_load_many = self._make_processor('load', True)

    @staticmethod
    def _copy_fields(
            fields: FieldDict, keys: Iterable[str],
            is_copying: Callable[[str], bool]) -> FieldDict:
        new_fields = {}
        for key in keys:
            if is_copying(key):
                new_fields[key] = fields[key]
        return new_fields

    @staticmethod
    def _set_fields(cls_or_obj, attrs: FieldDict):
        """Set fields for `Catalyst` class or its instance.
        Fields are bond to `cls_or_obj._field_dict` which are set separately
        on class or its instance, which works like class inheritance.
        """
        fields = {}
        fields.update(cls_or_obj._field_dict)  # inherit fields
        for attr, value in attrs.items():
            if isinstance(value, type) and issubclass(value, Field):
                raise TypeError(
                    f'Field for "{attr}" must be declared as a Field instance, '
                    f'not a class. Did you mean "{value.__name__}()"?')
            # automatic generate field name or key
            if isinstance(value, Field):
                if value.name is None:
                    value.name = cls_or_obj._format_field_name(attr)
                if value.key is None:
                    value.key = cls_or_obj._format_field_key(attr)
                fields[attr] = value
        cls_or_obj._field_dict = fields

    @staticmethod
    def _process_one(
            data: Any,
            all_errors: bool,
            assign_getter: Callable,
            partial_fields: Iterable[tuple],
            except_exception: ExceptionType):
        """Process one object using fields and catalyst options."""
        # According to the type of `data`, assign a function to get field value from `data`
        get_value = assign_getter(data)

        valid_data, errors, invalid_data = {}, {}, {}

        for field, source, target, required, default, field_handle in partial_fields:
            raw_value = missing
            try:
                if callable(default):
                    default = default()
                raw_value = get_value(data, source, default)
                if raw_value is missing:
                    if required:
                        field.error('required')
                    else:
                        continue

                valid_data[target] = field_handle(raw_value)
            except except_exception as e:
                # collect errors and invalid data
                if isinstance(e, ValidationError) and isinstance(e.msg, BaseResult):
                    # distribute nested data in BaseResult
                    valid_data[target] = e.msg.valid_data
                    errors[source] = e.msg.errors
                    invalid_data[source] = e.msg.invalid_data
                else:
                    errors[source] = e
                    if raw_value is not missing:
                        invalid_data[source] = raw_value
                if not all_errors:
                    break

        return valid_data, errors, invalid_data

    @staticmethod
    def _process_many(data: Sequence, all_errors: bool, process_one: Callable):
        """Process multiple objects using fields and catalyst options."""
        valid_data, errors, invalid_data = [], {}, {}
        for i, item in enumerate(data):
            result = process_one(item, raise_error=False)
            valid_data.append(result.valid_data)
            if not result.is_valid:
                errors[i] = result.errors
                invalid_data[i] = result.invalid_data
                if not all_errors:
                    break
        return valid_data, errors, invalid_data

    def _make_processor(self, name: str, many: bool) -> Callable:
        """Create processor for dumping and loading processes. And wrap basic
        main process with pre and post processes. Determine parameters for
        different processes in advance to reduce processing time.
        """
        if name == 'dump':
            ResultClass = DumpResult
        elif name == 'load':
            ResultClass = LoadResult
        else:
            raise ValueError("Argument `name` must be 'dump' or 'load'.")

        all_errors = self.all_errors
        except_exception = self.except_exception
        if many:
            main_process = partial(
                self._process_many,
                all_errors=all_errors,
                process_one=getattr(self, name))
            method_name = name + '_many'
        else:
            method_name = name
            if name == 'dump':
                assign_getter = self._assign_dump_getter
                field_dict = self._dump_field_dict
                field_method = self.dump_method
                source_attr = 'name'
                target_attr = 'key'
                default_attr = 'dump_default'
                required_attr = 'dump_required'
            else:
                assign_getter = self._assign_load_getter
                field_dict = self._load_field_dict
                field_method = self.load_method
                source_attr = 'key'
                target_attr = 'name'
                default_attr = 'load_default'
                required_attr = 'load_required'

            partial_fields = []
            for field in field_dict.values():
                source = getattr(field, source_attr)
                target = getattr(field, target_attr)
                required = getattr(field, required_attr)
                default = getattr(field, default_attr)
                field_handle = getattr(field, field_method)
                partial_fields.append((field, source, target, required, default, field_handle))
            main_process = partial(
                self._process_one,
                all_errors=all_errors,
                assign_getter=assign_getter,
                partial_fields=partial_fields,
                except_exception=except_exception)

        # assign params as closure variables for processor
        pre_process_name = f'pre_{method_name}'
        post_process_name = f'post_{method_name}'
        pre_process = getattr(self, pre_process_name)
        post_process = getattr(self, post_process_name)
        process_aliases = self.process_aliases
        default_raise_error = self.raise_error

        def integrated_process(data, raise_error):
            if raise_error is None:
                raise_error = default_raise_error

            try:
                # pre process
                process_name = pre_process_name
                valid_data = pre_process(data)

                # main process
                process_name = method_name
                valid_data, errors, invalid_data = main_process(valid_data)

                # post process
                if not errors:
                    process_name = post_process_name
                    valid_data = post_process(valid_data, original_data=data)
            except except_exception as e:
                # handle error which raised during processing
                key = process_aliases.get(process_name, process_name)
                errors = {key: e}
                invalid_data = data
                if many:
                    valid_data = []
                else:
                    valid_data = {}

            result = ResultClass(valid_data, errors, invalid_data)
            if errors and raise_error:
                raise ValidationError(result)
            return result

        return integrated_process

    def _process_args(self, func: Callable, processor: Callable) -> Callable:
        """Decorator for handling args by catalyst before function is called.
        The wrapper function takes args as same as args of the raw function.
        If args are invalid, error will be raised. In general, `*args` should
        be handled by `ListField`, and `**kwargs` should be handled by `NestedField`.
        """
        sig = inspect.signature(func)
        @wraps(func)
        def wrapper(*args, **kwargs):
            ba = sig.bind(*args, **kwargs)
            result = processor(ba.arguments, raise_error=True)
            ba.arguments.update(result.valid_data)
            return func(*ba.args, **ba.kwargs)
        return wrapper

    def dump(self, data: Any, raise_error: bool = None) -> DumpResult:
        return self._do_dump(data, raise_error)

    def load(self, data: Any, raise_error: bool = None) -> LoadResult:
        return self._do_load(data, raise_error)

    def dump_many(self, data: Sequence, raise_error: bool = None) -> DumpResult:
        return self._do_dump_many(data, raise_error)

    def load_many(self, data: Sequence, raise_error: bool = None) -> LoadResult:
        return self._do_load_many(data, raise_error)

    def dump_args(self, func: Callable) -> Callable:
        return self._process_args(func, self.dump)

    def load_args(self, func: Callable = None) -> Callable:
        return self._process_args(func, self.load)

    # pre and post processes
    def pre_dump(self, data):
        return data

    def post_dump(self, data, original_data):
        return data

    def pre_load(self, data):
        return data

    def post_load(self, data, original_data):
        return data

    def pre_dump_many(self, data):
        return data

    def post_dump_many(self, data, original_data):
        return data

    def pre_load_many(self, data):
        return data

    def post_load_many(self, data, original_data):
        return data

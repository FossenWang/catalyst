"""Catalyst class and its metaclass."""

import inspect

from typing import Iterable, Callable, Sequence, Any, Mapping
from functools import wraps, partial

from .base import CatalystABC
from .fields import BaseField, FieldDict
from .groups import FieldGroup
from .exceptions import ValidationError, ExceptionType
from .utils import (
    missing, assign_attr_or_item_getter, assign_item_getter,
    LoadResult, DumpResult, BaseResult, bind_attrs, no_processing
)


def _get_fields(fields: dict):
    """Collect fields from dict."""
    new_fields: FieldDict = {}
    for name, field in fields.items():
        if isinstance(field, type) and issubclass(field, BaseField):
            raise TypeError(
                f'Field for "{name}" must be declared as a Field instance, '
                f'not a class. Did you mean "{field.__name__}()"?')

        if isinstance(field, BaseField):
            new_fields[name] = field
    return new_fields


def _get_fields_from_classes(classes: Iterable[type]):
    """Collect fields from base classes, following method resolution order."""
    fields = {}
    for klass in reversed(classes):
        if issubclass(klass, CatalystABC):
            fields.update(_get_fields(klass.fields))
        else:
            for base in klass.mro()[-2::-1]:
                fields.update(_get_fields(base.__dict__))
    return fields


def _get_fields_from_instance(obj):
    """Collect fields from instance."""
    if isinstance(obj, CatalystABC):
        fields = obj.fields
    else:
        fields = {attr: getattr(obj, attr) for attr in dir(obj)}
    return _get_fields(fields)


def _set_fields(cls_or_obj, fields: FieldDict):
    """Set fields for `Catalyst` class or its instance.
    Generate "field.name" or "field.key" if it is None.
    """
    for attr, field in fields.items():
        if field.name is None:
            field.name = cls_or_obj._format_field_name(attr)
        if field.key is None:
            field.key = cls_or_obj._format_field_key(attr)

        # inject fields that FieldGroup declared
        if isinstance(field, FieldGroup):
            field.set_fields(fields)

    cls_or_obj.fields = fields


class CatalystMeta(type):
    """Metaclass for `Catalyst` class. Binds fields to `fields` attribute."""

    def __new__(cls, name, bases, attrs):
        new_cls = super().__new__(cls, name, bases, attrs)
        fields = _get_fields_from_classes(bases)
        fields.update(_get_fields(attrs))
        _set_fields(new_cls, fields)
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

    DumpResult = DumpResult
    LoadResult = LoadResult

    fields: FieldDict = {}

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
            fields = self.fields.copy()
            if isinstance(schema, Mapping):
                new_fields = _get_fields(schema)
            elif isinstance(schema, type):
                new_fields = _get_fields_from_classes([schema])
            else:
                new_fields = _get_fields_from_instance(schema)
            fields.update(new_fields)
            _set_fields(self, fields)

        # include fields
        if include is None:
            include = self.fields.keys()
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
            self._dump_fields = self._copy_fields(
                self.fields, dump_include,
                lambda key: not self.fields[key].no_dump)
            self._load_fields = self._copy_fields(
                self.fields, load_include,
                lambda key: not self.fields[key].no_load)
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
    def _process_one(
            data: Any,
            all_errors: bool,
            assign_getter: Callable,
            partial_fields: Iterable[tuple],
            partial_groups: Iterable[tuple],
            except_exception: ExceptionType):
        """Process one object using fields and catalyst options."""
        # According to the type of `data`, assign a function to get field value from `data`
        get_value = assign_getter(data)

        valid_data, errors, invalid_data = {}, {}, {}

        # process data for each fields
        for field, source, target, required, default, field_method in partial_fields:
            raw_value = missing
            try:
                if callable(default):
                    default = default()
                raw_value = get_value(data, source, default)
                if raw_value is missing:
                    if required:
                        field.error('required')
                    continue

                valid_data[target] = field_method(raw_value)
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

        # field groups depend on fields, if error occurs, do not continue
        if errors:
            return valid_data, errors, invalid_data

        # process data for each field groups
        for group_method, error_key, source_target_pairs in partial_groups:
            try:
                valid_data = group_method(valid_data, data)
            except except_exception as e:
                # set error and move invalid data
                errors[error_key] = e
                for source, target in source_target_pairs:
                    if target in valid_data:
                        invalid_data[source] = valid_data.pop(target)
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
            ResultClass = self.DumpResult
        elif name == 'load':
            ResultClass = self.LoadResult
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
                field_dict = self._dump_fields
                field_method_name = self.dump_method
                source_attr = 'name'
                target_attr = 'key'
                default_attr = 'dump_default'
                required_attr = 'dump_required'
            else:
                assign_getter = self._assign_load_getter
                field_dict = self._load_fields
                field_method_name = self.load_method
                source_attr = 'key'
                target_attr = 'name'
                default_attr = 'load_default'
                required_attr = 'load_required'

            partial_fields, partial_groups = [], []
            for field in field_dict.values():
                if isinstance(field, FieldGroup):
                    group: FieldGroup = field
                    group_method = getattr(group, method_name)
                    group_method = self._modify_processer_parameters(group_method)
                    error_key = getattr(group, source_attr)
                    source_target_pairs = []
                    for f in group.fields.values():
                        source = getattr(f, source_attr)
                        target = getattr(f, target_attr)
                        source_target_pairs.append((source, target))
                    partial_groups.append((group_method, error_key, source_target_pairs))
                    continue

                source = getattr(field, source_attr)
                target = getattr(field, target_attr)
                required = getattr(field, required_attr)
                default = getattr(field, default_attr)
                field_method = getattr(field, field_method_name)
                partial_fields.append((field, source, target, required, default, field_method))
            main_process = partial(
                self._process_one,
                all_errors=all_errors,
                assign_getter=assign_getter,
                partial_fields=partial_fields,
                partial_groups=partial_groups,
                except_exception=except_exception)

        # assign params as closure variables for processor
        pre_process_name = f'pre_{method_name}'
        post_process_name = f'post_{method_name}'
        pre_process = getattr(self, pre_process_name)
        post_process = getattr(self, post_process_name)
        post_process = self._modify_processer_parameters(post_process)
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

    def _modify_processer_parameters(self, func):
        """Modify the parameters of the processer function.
        Ignore `original_data` if it's not one of the parameters.
        """
        sig = inspect.signature(func)
        if 'original_data' not in sig.parameters:
            @wraps(func)
            def wrapper(data, original_data=None):
                return func(data)
            return wrapper
        return func

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

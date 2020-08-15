"""Catalyst class and its metaclass."""

import inspect
from collections import namedtuple
from typing import Iterable, Callable, Any, Mapping
from functools import wraps, partial

from .base import CatalystABC
from .fields import BaseField, FieldDict, Field
from .groups import FieldGroup
from .exceptions import ValidationError, ExceptionType
from .utils import (
    missing, assign_attr_or_item_getter, assign_item_getter,
    LoadResult, DumpResult, BaseResult, no_processing,
    bind_attrs, bind_not_ellipsis_attrs,
)


# type hints
PartialFields = namedtuple('PartialFields', [
    'field', 'source', 'target', 'required', 'default', 'field_method'])
PartialGroups = namedtuple('PartialGroups', [
    'group_method', 'error_key', 'source_target_pairs'])


def _override_fields(fields: FieldDict, attrs: dict):
    """Collect fields from dict, override fields and remove non fields."""
    for name, obj in attrs.items():
        if isinstance(obj, type) and issubclass(obj, BaseField):
            raise TypeError(
                f'Field for "{name}" must be declared as a Field instance, '
                f'not a class. Did you mean "{obj.__name__}()"?')

        if isinstance(obj, BaseField):
            fields[name] = obj  # override Field
        elif name in fields:
            del fields[name]  # remove non Field
    return fields


def _get_fields_from_classes(fields: FieldDict, classes: Iterable[type]):
    """Collect fields from base classes, following method resolution order."""
    for klass in reversed(classes):
        if issubclass(klass, CatalystABC):
            _override_fields(fields, klass.fields)
        else:
            # reverse and ignore <class 'object'>
            for base in klass.mro()[-2::-1]:
                _override_fields(fields, base.__dict__)
    return fields


def _get_fields_from_instance(fields: FieldDict, obj):
    """Collect fields from instance."""
    if isinstance(obj, CatalystABC):
        attrs = obj.fields
    else:
        attrs = {attr: getattr(obj, attr) for attr in dir(obj)}
    return _override_fields(fields, attrs)


def _set_fields(cls_or_obj, fields: FieldDict):
    """Set fields for `Catalyst` class or its instance.
    Generate `Field.name` or `Field.key` if it is None.
    """
    for name, field in fields.items():
        if field.name is None:
            field.name = cls_or_obj._format_field_name(name)
        if field.key is None:
            field.key = cls_or_obj._format_field_key(name)

    # inject fields that FieldGroup declared, after all fields are formatted
    for field in fields.values():
        if isinstance(field, FieldGroup):
            field.set_fields(fields)

    cls_or_obj.fields = fields


class CatalystMeta(type):
    """Metaclass for `Catalyst` class. Binds fields to `fields` attribute."""

    def __new__(cls, name, bases, attrs):
        new_cls = super().__new__(cls, name, bases, attrs)
        fields = {}
        _get_fields_from_classes(fields, bases)
        _override_fields(fields, attrs)
        _set_fields(new_cls, fields)
        return new_cls


class Catalyst(CatalystABC, metaclass=CatalystMeta):
    """Base Catalyst class for converting complex datatypes to and from
    native Python datatypes.

    Some instantiation params can set default values by class variables.
    The available params are `schema`, `raise_error`, `all_errors`,
    `except_exception`, `process_aliases`, `DumpResult` and `LoadResult`.

    :param schema: A dict or instance or class which contains fields. This
        is a convenient way to avoid name clashes when fields are Python
        keywords or conflict with other attributes.
    :param dump_required: Raise error if the field value doesn't exist.
        The `Field.dump_required` will take priority, if it is not `None`.
    :param load_required: Similar to `dump_required`.
    :param dump_default: The default value when the field value doesn't exist.
        If set, `dump_required` has no effect.
        Particularly, the `missing` object means that this field will not exist
        in result, and `None` means that default value is `None`.
        The `Field.dump_default` will take priority, if it is not `missing`.
    :param load_default: Similar to `dump_default`.
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
    raise_error = False
    all_errors = True
    except_exception: ExceptionType = Exception
    process_aliases = {}

    dump_required = True
    load_required = False
    dump_default = missing
    load_default = missing

    dump_result_class = DumpResult
    load_result_class = LoadResult

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
            raise_error: bool = None,
            all_errors: bool = None,
            except_exception: ExceptionType = None,
            process_aliases: Mapping[str, str] = None,
            dump_required: bool = None,
            load_required: bool = None,
            dump_default: Any = ...,
            load_default: Any = ...,
            include: Iterable[str] = None,
            exclude: Iterable[str] = None,
            dump_include: Iterable[str] = None,
            dump_exclude: Iterable[str] = None,
            load_include: Iterable[str] = None,
            load_exclude: Iterable[str] = None):
        bind_attrs(
            self,
            schema=schema,
            raise_error=raise_error,
            all_errors=all_errors,
            except_exception=except_exception,
            process_aliases=process_aliases,
            dump_required=dump_required,
            load_required=load_required,
        )
        # `None` is meaningful to `dump_default` and `load_default`,
        # use `...` to represent that the arguments are not given
        # which also provides type hints.
        bind_not_ellipsis_attrs(
            self,
            dump_default=dump_default,
            load_default=load_default,
        )

        # set fields from a dict or instance or class
        schema = self.schema
        if schema:
            fields = self.fields.copy()
            if isinstance(schema, Mapping):
                _override_fields(fields, schema)
            elif isinstance(schema, type):
                _get_fields_from_classes(fields, [schema])
            else:
                _get_fields_from_instance(fields, schema)
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
            raise ValueError(f'Field "{error.args[0]}" does not exist.') from error

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
            partial_fields: Iterable[PartialFields],
            partial_groups: Iterable[PartialGroups],
            except_exception: ExceptionType):
        """Process one object using fields and catalyst options."""
        # According to the type of `data`, assign a function to get field value from `data`
        get_value = assign_getter(data)

        valid_data, errors, invalid_data = {}, {}, {}

        # process data for each fields
        for field, source, target, required, default, field_method in partial_fields:
            value = missing
            try:
                value = get_value(data, source, missing)

                if value is missing:
                    value = default() if callable(default) else default

                if value is not missing:
                    value = field_method(value)

                if value is missing:
                    if required:
                        raise field.error('required')
                else:
                    valid_data[target] = value
            except except_exception as e:
                if isinstance(e, ValidationError) and isinstance(e.detail, BaseResult):
                    detail: BaseResult = e.detail
                    # distribute nested data in BaseResult
                    valid_data[target] = detail.valid_data
                    errors[source] = detail.errors
                    invalid_data[source] = detail.invalid_data
                else:
                    # collect errors and invalid data
                    errors[source] = e
                    if value is not missing:
                        invalid_data[source] = value
                if not all_errors:
                    break

        # field groups depend on fields, if error occurs, do not continue
        if errors:
            return valid_data, errors, invalid_data

        # process data for each field groups
        for group_method, error_key, source_target_pairs in partial_groups:
            try:
                valid_data = group_method(valid_data, original_data=data)
            except except_exception as e:
                if isinstance(e, ValidationError) and isinstance(e.detail, BaseResult):
                    detail: BaseResult = e.detail
                    # distribute nested data in BaseResult
                    try:
                        valid_data.update(detail.valid_data)
                        errors.update(detail.errors)
                        invalid_data.update(detail.invalid_data)
                    except (ValueError, TypeError):
                        errors[error_key] = detail.format_errors()
                else:
                    # collect errors and invalid data
                    errors[error_key] = e
                    for source, target in source_target_pairs:
                        if target in valid_data:
                            invalid_data[source] = valid_data.pop(target)
                if not all_errors:
                    break
        return valid_data, errors, invalid_data

    @staticmethod
    def _process_many(data: Iterable, all_errors: bool, process_one: Callable):
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
            result_class = self.dump_result_class
        elif name == 'load':
            result_class = self.load_result_class
        else:
            raise ValueError('Argument "name" must be "dump" or "load".')

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
                source_attr = 'name'
                target_attr = 'key'
                default_attr = 'dump_default'
                required_attr = 'dump_required'
            else:
                assign_getter = self._assign_load_getter
                field_dict = self._load_fields
                source_attr = 'key'
                target_attr = 'name'
                default_attr = 'load_default'
                required_attr = 'load_required'
            # the required options for all fields
            general_required = getattr(self, required_attr)
            general_default = getattr(self, default_attr)

            partial_fields, partial_groups = [], []
            for field in field_dict.values():
                if isinstance(field, FieldGroup):
                    # get partial arguments from FieldGroup
                    group: FieldGroup = field
                    group_method = getattr(group, method_name)
                    group_method = self._modify_processer_parameters(group_method)
                    error_key = getattr(group, source_attr)
                    source_target_pairs = []
                    for f in group.fields.values():
                        source = getattr(f, source_attr)
                        target = getattr(f, target_attr)
                        source_target_pairs.append((source, target))
                    partial_groups.append(
                        PartialGroups(group_method, error_key, source_target_pairs))
                elif isinstance(field, Field):
                    # get partial arguments from Field
                    field_method = getattr(field, method_name)
                    source = getattr(field, source_attr)
                    target = getattr(field, target_attr)
                    required = getattr(field, required_attr)
                    if required is None:
                        required = general_required
                    default = getattr(field, default_attr)
                    if default is missing:
                        default = general_default
                    partial_fields.append(
                        PartialFields(field, source, target, required, default, field_method))
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
            """The actual execution function to do dumping and loading."""
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

            result = result_class(valid_data, errors, invalid_data)
            if errors and raise_error:
                raise ValidationError(msg=result.format_errors(), detail=result)
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
        """Serialize `data` according to defined fields."""
        return self._do_dump(data, raise_error)

    def load(self, data: Any, raise_error: bool = None) -> LoadResult:
        """Deserialize `data` according to defined fields."""
        return self._do_load(data, raise_error)

    def dump_many(self, data: Iterable, raise_error: bool = None) -> DumpResult:
        """Serialize multiple objects."""
        return self._do_dump_many(data, raise_error)

    def load_many(self, data: Iterable, raise_error: bool = None) -> LoadResult:
        """Deserialize multiple objects."""
        return self._do_load_many(data, raise_error)

    def dump_args(self, func: Callable) -> Callable:
        """Decorator for serializing arguments of the function."""
        return self._process_args(func, self.dump)

    def load_args(self, func: Callable = None) -> Callable:
        """Decorator for deserializing arguments of the function."""
        return self._process_args(func, self.load)

    # pre and post processes
    def pre_dump(self, data):
        return data

    def post_dump(self, data, original_data=None):
        return data

    def pre_load(self, data):
        return data

    def post_load(self, data, original_data=None):
        return data

    def pre_dump_many(self, data):
        return data

    def post_dump_many(self, data, original_data=None):
        return data

    def pre_load_many(self, data):
        return data

    def post_load_many(self, data, original_data=None):
        return data

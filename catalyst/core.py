import inspect

from typing import Dict, Iterable, Callable, Sequence, Any, Mapping
from functools import wraps, partial

from .fields import Field, NestedField
from .exceptions import ValidationError
from .utils import (
    missing, assign_attr_or_item_getter, assign_item_getter,
    LoadResult, DumpResult, BaseResult, OptionBox
)


FieldDict = Dict[str, Field]


class BaseCatalyst:
    """Base Catalyst class.

    :param schema: A dict or instance or class which has fields. This is a
        convenient way to avoid name clashes when fields are Python keywords
        or conflict with other attributes.
        ** It should be noted that "private" variables which prefixed with
        an underscore (e.g. _spam) will not be considered when `schema` is
        an instance or class. If an underscore prefixed name is necessary,
        use dict `schema`.
        Remmber that the attribute name of `Catalyst` object can be different
        with "data" object. `Field.name` defines where to access value.

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
    _field_dict = {}  # type: FieldDict

    class Options(OptionBox):
        dump_method = 'format'
        load_method = 'load'
        raise_error = False
        all_errors = True
        schema = None
        # error keys used for error process, be careful with attribute inheriting
        error_keys = {}

    # assign getter for dumping & loading
    _assign_dump_getter = staticmethod(assign_attr_or_item_getter)
    _assign_load_getter = staticmethod(assign_item_getter)

    @staticmethod
    def _format_field_key(key):
        return key

    @staticmethod
    def _format_field_name(name):
        return name

    @staticmethod
    def _copy_fields(
            fields: FieldDict, keys: Iterable[str],
            is_copying: Callable[[str], bool]) -> FieldDict:
        new_fields = {}  # type: FieldDict
        for key in keys:
            if is_copying(key):
                new_fields[key] = fields[key]
        return new_fields

    @staticmethod
    def _set_fields(cls_or_obj, attrs):
        raise NotImplementedError()

    def __init__(
            self,
            schema: Any = None,
            include: Iterable[str] = None,
            exclude: Iterable[str] = None,
            raise_error: bool = None,
            all_errors: bool = None,
            error_keys: Mapping[str, str] = None,
            dump_include: Iterable[str] = None,
            dump_exclude: Iterable[str] = None,
            dump_method: str = None,
            load_include: Iterable[str] = None,
            load_exclude: Iterable[str] = None,
            load_method: str = None,
            **kwargs):
        self.opts = self.Options(
            schema=schema,
            raise_error=raise_error,
            all_errors=all_errors,
            error_keys=error_keys,
            dump_method=dump_method,
            load_method=load_method,
            **kwargs,
        )

        if self.opts.dump_method not in {'dump', 'format', 'validate'}:
            raise ValueError(
                "Attribute `opts.dump_method` must be in ('dump', 'format', 'validate').")
        if self.opts.load_method not in {'load', 'parse', 'validate'}:
            raise ValueError(
                "Attribute `opts.load_method` must be in ('load', 'parse', 'validate').")

        # set fields from a dict or non `Catalyst` class
        schema = self.opts.schema
        if schema:
            if isinstance(schema, Mapping):
                attrs = schema
            else:
                attrs = {
                    name: getattr(schema, name) for name in dir(schema)
                    if not name.startswith('_')}  # ignore private variables
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
                lambda key: not self._field_dict[key].opts.no_dump)
            self._load_field_dict = self._copy_fields(
                self._field_dict, load_include,
                lambda key: not self._field_dict[key].opts.no_load)
        except KeyError as error:
            raise ValueError(f"Field '{error.args[0]}' does not exist.") from error

        # make processors when initializing for shorter run time
        self._do_dump = self._make_processor('dump', False)
        self._do_load = self._make_processor('load', False)
        self._do_dump_many = self._make_processor('dump', True)
        self._do_load_many = self._make_processor('load', True)

    @staticmethod
    def _process_one(
            data: Any,
            all_errors: bool,
            assign_getter: Callable,
            field_dict: FieldDict,
            field_method: str,
            source_attr: str,
            target_attr: str,
            default_attr: str,
            required_attr: str):
        # According to the type of `data`, assign a function to get field value from `data`
        get_value = assign_getter(data)

        valid_data, errors, invalid_data = {}, {}, {}

        for field in field_dict.values():
            source = getattr(field, source_attr)
            target = getattr(field, target_attr)
            default = getattr(field, default_attr)
            required = getattr(field.opts, required_attr)

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

                valid_data[target] = getattr(field, field_method)(raw_value)
            except Exception as e:
                # collect errors and invalid data
                if isinstance(e, ValidationError) and isinstance(e.msg, BaseResult):
                    # distribute nested data in BaseResult
                    valid_data[target] = e.msg.valid_data
                    errors[source] = e.msg.errors
                    invalid_data[source] = e.msg.invalid_data
                else:
                    errors[source] = e
                    invalid_data[source] = raw_value
                if not all_errors:
                    break

        return valid_data, errors, invalid_data

    @staticmethod
    def _process_many(data: Sequence, all_errors: bool, process_one: Callable):
        valid_data, errors, invalid_data = [], {}, {}
        for i, item in enumerate(data):
            result = process_one(item, raise_error=False, all_errors=all_errors)
            valid_data.append(result.valid_data)
            if not result.is_valid:
                errors[i] = result.errors
                invalid_data[i] = result.invalid_data
                if not all_errors:
                    break
        return valid_data, errors, invalid_data

    def _make_processor(self, name: str, many: bool) -> Callable:
        """Create processor for dumping and loading processes. And wrap basic
        main process with pre and post processes. To avoid assigning params
        every time a processor is called, the params are stored in the closure.
        """
        # assign params as closure variables for processor
        if name == 'dump':
            ResultClass = DumpResult
        elif name == 'load':
            ResultClass = LoadResult
        else:
            raise ValueError("Argument `name` must be 'dump' or 'load'.")

        if many:
            process_one = getattr(self, name)
            main_process = partial(self._process_many, process_one=process_one)
            method_name = name + '_many'
        else:
            method_name = name
            if name == 'dump':
                main_process = partial(
                    self._process_one,
                    assign_getter=self._assign_dump_getter,
                    field_dict=self._dump_field_dict,
                    field_method=self.opts.dump_method,
                    source_attr='name',
                    target_attr='key',
                    default_attr='dump_default',
                    required_attr='dump_required')
            else:
                main_process = partial(
                    self._process_one,
                    assign_getter=self._assign_load_getter,
                    field_dict=self._load_field_dict,
                    field_method=self.opts.load_method,
                    source_attr='key',
                    target_attr='name',
                    default_attr='load_default',
                    required_attr='load_required')

        pre_process_name = f'pre_{method_name}'
        post_process_name = f'post_{method_name}'
        pre_process = getattr(self, pre_process_name)
        post_process = getattr(self, post_process_name)
        error_keys = self.opts.error_keys
        default_raise_error = self.opts.raise_error
        default_all_errors = self.opts.all_errors

        def integrated_process(data, raise_error, all_errors):
            if raise_error is None:
                raise_error = default_raise_error
            if all_errors is None:
                all_errors = default_all_errors

            try:
                # pre process
                process_name = pre_process_name
                valid_data = pre_process(data)

                # main process
                process_name = method_name
                valid_data, errors, invalid_data = main_process(valid_data, all_errors=all_errors)

                # post process
                if not errors:
                    process_name = post_process_name
                    valid_data = post_process(valid_data, original_data=data)
            except Exception as e:
                # handle error which raised during processing
                error_key = error_keys.get(process_name, process_name)
                errors = {error_key: e}
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

    def _process_args(
            self, func: Callable = None, processor: Callable = None, all_errors: bool = None,
        ) -> Callable:
        """Decorator for handling args by catalyst before function is called.
        The wrapper function takes args as same as args of the raw function.
        If args are invalid, error will be raised. In general, `*args` should
        be handled by `ListField`, and `**kwargs` should be handled by `NestedField`.
        """
        if func:
            sig = inspect.signature(func)
            @wraps(func)
            def wrapper(*args, **kwargs):
                ba = sig.bind(*args, **kwargs)
                result = processor(ba.arguments, raise_error=True, all_errors=all_errors)
                ba.arguments.update(result.valid_data)
                return func(*ba.args, **ba.kwargs)
            return wrapper
        return partial(self._process_args, processor=processor, all_errors=all_errors)

    def dump(
            self,
            data: Any,
            raise_error: bool = None,
            all_errors: bool = None,
        ) -> DumpResult:
        return self._do_dump(data, raise_error, all_errors)

    def load(
            self,
            data: Any,
            raise_error: bool = None,
            all_errors: bool = None,
        ) -> LoadResult:
        return self._do_load(data, raise_error, all_errors)

    def dump_many(
            self,
            data: Sequence,
            raise_error: bool = None,
            all_errors: bool = None,
        ) -> DumpResult:
        return self._do_dump_many(data, raise_error, all_errors)

    def load_many(
            self,
            data: Sequence,
            raise_error: bool = None,
            all_errors: bool = None,
        ) -> LoadResult:
        return self._do_load_many(data, raise_error, all_errors)

    def dump_args(self, func: Callable = None, all_errors: bool = None) -> Callable:
        return self._process_args(func, self.dump, all_errors)

    def load_args(self, func: Callable = None, all_errors: bool = None) -> Callable:
        return self._process_args(func, self.load, all_errors)

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


class CatalystMeta(type):
    """Metaclass for `Catalyst` class. Binds fields to `_field_dict` attribute."""

    def __new__(cls, name, bases, attrs):
        new_cls = super().__new__(cls, name, bases, attrs)
        if not (isinstance(new_cls.Options, type) and issubclass(new_cls.Options, OptionBox)):
            raise TypeError('Class attribute `Options` must inherit from `OptionBox`.')

        new_cls._set_fields(new_cls, attrs)
        return new_cls


class Catalyst(BaseCatalyst, metaclass=CatalystMeta):
    __doc__ = BaseCatalyst.__doc__

    @staticmethod
    def _set_fields(cls_or_obj: BaseCatalyst, attrs: FieldDict):
        """Set fields for `Catalyst` class or its instance.
        Fields are bond to `cls_or_obj._field_dict` which are set separately
        on class or its instance, which works like class inheritance.

        :param cls_or_obj: `Catalyst` class or its instance.
        :param attrs: a dict that keys are name and values are `Field`.
        """
        fields = {}  # type: FieldDict
        # inherit fields
        fields.update(cls_or_obj._field_dict)

        for attr, value in attrs.items():
            # init calalyst object
            if isinstance(value, CatalystMeta):
                value = value()
            # wrap catalyst object as NestedField
            if isinstance(value, BaseCatalyst):
                value = NestedField(value)
            # automatic generate field name or key
            if isinstance(value, Field):
                if value.name is None:
                    value.name = cls_or_obj._format_field_name(attr)
                if value.key is None:
                    value.key = cls_or_obj._format_field_key(attr)

                fields[attr] = value

        cls_or_obj._field_dict = fields

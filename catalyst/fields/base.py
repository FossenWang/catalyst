import inspect
from functools import partial

from typing import Any, Iterable, Union, Dict, Callable as CallableType

from ..utils import (
    ErrorMessageMixin, missing, no_processing,
    bind_attrs, bind_not_ellipsis_attrs,
)
from ..validators import MemberValidator, NonMemberValidator


ValidatorType = CallableType[[Any], None]

MultiValidator = Union[ValidatorType, Iterable[ValidatorType]]


class BaseField(ErrorMessageMixin):
    """Basic field class for converting objects.

    Instantiation params can set default values by class variables.

    :param name: The source field to get the value from when dumping data.
        The target field to set the value to when loading data. For example,
        ``result[key] = field.dump(data[field.name])``, and
        ``result[name] = field.load(data[field.key])``.
    :param key: The source field to get the value from when loading data.
        The target field to set the value to when dumping data.
    :param no_dump: Whether to skip this field during dumping.
    :param no_load: Whether to skip this field during loading.
    :param error_messages: A dict of error messages.
    """
    no_dump = False
    no_load = False

    name: str
    key: str
    # Aliases for `name` and `key`
    dump_source = property(lambda self: self.name)
    dump_target = property(lambda self: self.key)
    load_source = property(lambda self: self.key)
    load_target = property(lambda self: self.name)

    def __init__(
            self,
            name: str = None,
            key: str = None,
            no_dump: bool = None,
            no_load: bool = None,
            error_messages: Dict[str, str] = None):
        self.name = name
        self.key = key
        self.collect_error_messages(error_messages)
        bind_attrs(self, no_dump=no_dump, no_load=no_load)

    def override_method(
            self, func: CallableType = None, attr: str = None,
            obj_name='field', original_name='original_method'):
        """Override a method of the field instance. Inject field instance or covered method
        as argments into the function according to argument name.

        Example:

            field.override_method(function, 'format')

            @field.override_method(attr='format')
            def function(value):
                return value

            field.set_format = field.override_method(attr='format')

            @field.set_format
            def function(self, value):
                return value

            @field.set_format
            def function(value, field, original_method):
                return original_method(value)

            @field.override_method(attr='format', obj_name='obj', original_name='old')
            def function(value, obj, old):
                return old(value)

        :param func: The function to override. The value will be passed to the first argument.
            Particularly, if the first argument is `self`, the field instance will be injected,
            and value will be the second argument.
            If argments like "field", "original_method" or "**kwargs" exist, the field instance
            or covered method will be passed.
        :param attr: The attribute to be overrided.
        :param obj_name: The argment name of the instence itself.
        :param original_name: The argment name of the original method.
        """
        if func is None:
            return partial(
                self.override_method, attr=attr,
                obj_name=obj_name, original_name=original_name)

        sig = inspect.signature(func)
        kwargs = {}
        # inject args if the last parameter is keyword arguments
        for param in reversed(sig.parameters.values()):
            if param.kind is inspect._VAR_KEYWORD:
                kwargs[obj_name] = self
                kwargs[original_name] = getattr(self, attr)
            break
        # inject args if parameter name matches
        if not kwargs:
            if obj_name in sig.parameters:
                kwargs[obj_name] = self
            if original_name in sig.parameters:
                kwargs[original_name] = getattr(self, attr)

        if sig.parameters:
            first_arg = next(iter(sig.parameters))
            # inject `self` if it's the first argment of `func`
            if first_arg == 'self':
                kwargs.pop('self', None)
                func = partial(func, self)

            # kwargs can't be first
            for arg_name in kwargs:
                if first_arg == arg_name:
                    raise TypeError(f'The first argment of "{func}" can not be "{arg_name}".')

        if kwargs:
            func = partial(func, **kwargs)

        setattr(self, attr, func)
        return func

    def dump(self, *args, **kwargs):
        raise NotImplementedError

    def load(self, *args, **kwargs):
        raise NotImplementedError


class Field(BaseField):
    """Handles only a single field value of the input data, and can not access
    the other field values. This does not process the value by default.

    :param formatter: The function that formats the field value during dumping,
        and which will override `Field.format`.
    :param parser: The function that parses the field value during loading,
        and which will override `Field.parse`.
    :param dump_required: Raise error if the field value doesn't exist.
    :param load_required: Similar to `dump_required`.
    :param dump_default: The default value when the field value doesn't exist.
        If set, `dump_required` has no effect.
        Particularly, the `missing` object means that this field will not exist
        in result, and `None` means that default value is `None`.
    :param load_default: Similar to `dump_default`.
    :param validators: Validator or collection of validators. The validator
        function is not required to return value, and should raise error
        directly if invalid.
        By default, validators are called during loading.
    :param allow_none: Whether the field value are allowed to be `None`.
        By default, this takes effect during loading.
    :param as_none: A collection of values that are treated as null.
    :param dump_none: The value which null values are convert to when dumping.
    :param load_none: The value which null values are convert to when loading.
    :param in_: A collection of valid values.
    :param not_in: A collection of invalid values.
    :param error_messages: Keys {'required', 'none', 'in', 'not_in'}.
    :param kwargs: Same as :class:`BaseField`.
    """
    dump_required = None
    load_required = None
    dump_default = ...
    load_default = ...
    validators = []
    allow_none = True
    as_none = (None,)
    dump_none = None
    load_none = None
    error_messages = {
        'required': 'Missing data for required field.',
        'none': 'Field may not be null.',
    }

    def __init__(
            self,
            formatter: CallableType = None,
            parser: CallableType = None,
            dump_required: bool = None,
            load_required: bool = None,
            dump_default: Any = ...,
            load_default: Any = ...,
            validators: MultiValidator = None,
            allow_none: bool = None,
            as_none: Iterable = None,
            dump_none: Any = ...,
            load_none: Any = ...,
            in_: Iterable = None,
            not_in: Iterable = None,
            **kwargs):
        super().__init__(**kwargs)
        bind_attrs(
            self,
            dump_required=dump_required,
            load_required=load_required,
            allow_none=allow_none,
            as_none=as_none,
        )
        # `None` is meaningful to `dump_default` and `load_default`,
        # use `...` to represent that the arguments are not given
        # which also provides type hints.
        bind_not_ellipsis_attrs(
            self,
            dump_default=dump_default,
            load_default=load_default,
            dump_none=dump_none,
            load_none=load_none,
        )

        if formatter is not None:
            self.set_format(formatter)
        if parser is not None:
            self.set_parse(parser)
        self.set_validators(validators if validators else self.validators)
        if in_:
            msg = self.error_messages.get('in')
            self.add_validator(MemberValidator(in_, msg))
        if not_in:
            msg = self.error_messages.get('not_in')
            self.add_validator(NonMemberValidator(not_in, msg))

    def set_format(self, func: CallableType = None, **kwargs):
        """Override `Field.format` method which will be called during dumping.
        See `BaseField.override_method` for more details.
        """
        return self.override_method(func, 'format', **kwargs)

    def set_parse(self, func: CallableType = None, **kwargs):
        """Override `Field.parse` method which will be called during loading.
        See `BaseField.override_method` for more details.
        """
        return self.override_method(func, 'parse', **kwargs)

    @staticmethod
    def ensure_validators(validators: MultiValidator) -> list:
        """Make sure validators are callables."""
        if not isinstance(validators, Iterable):
            validators = [validators]

        for v in validators:
            if not callable(v):
                raise TypeError(
                    'Argument "validators" must be ether Callable '
                    'or Iterable which contained Callable.')
        return list(validators)

    def set_validators(self, validators: MultiValidator):
        """Replace all validators."""
        self.validators = self.ensure_validators(validators)
        return validators

    def add_validator(self, validator: ValidatorType):
        """Append a validator to list."""
        if not callable(validator):
            raise TypeError('Argument "validator" must be Callable.')
        self.validators.append(validator)
        return validator

    def validate(self, value):
        """Validate `value`, raise error if it is invalid."""
        if self.is_none(value):
            if self.allow_none:
                return
            raise self.error('none')
        for validator in self.validators:
            validator(value)

    validate_dump = staticmethod(no_processing)
    validate_load = validate

    def is_none(self, value):
        return any(value == none for none in self.as_none)

    def format(self, value):
        return value

    def dump(self, value):
        """Serialize `value` as native Python data type by validating and
        formatting. By default, it doesn't validate `value` during dumping,
        but you can override `validate_dump` method to perform validation.
        """
        self.validate_dump(value)

        if self.is_none(value):
            value = self.dump_none
        else:
            value = self.format(value)
        return value

    def parse(self, value):
        return value

    def load(self, value):
        """Deserialize `value` to an object by parsing and validating.
        The `parse` method can return missing, which means that
        the field key won't be present in the result.
        """
        if self.is_none(value):
            value = self.load_none
        else:
            value = self.parse(value)

        if value is not missing:
            self.validate_load(value)
        return value


# type hints
FieldDict = Dict[str, BaseField]

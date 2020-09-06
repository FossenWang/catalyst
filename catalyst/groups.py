"""FieldGroup classes for processing multiple fields."""

from typing import Callable, Iterable
from functools import partial

from .fields import BaseField, Field, FieldDict, NestedField, NumberField
from .utils import bind_attrs


class FieldGroup(BaseField):
    """Process multiple fields of the data, after all single fields being handled.
    The `FieldGroup` can directly modify the whole data, while :class:`Field` can only modify
    one field value of the data.

    :param declared_fields: The fields that need to be injected by :class:`Catalyst`.
        A list of field names, or character "*" which means all fields.
    :param kwargs: Same as :class:`BaseField`.
    """
    declared_fields: Iterable[str] = tuple()
    fields: FieldDict

    def __init__(self, declared_fields: Iterable[str] = None, **kwargs):
        super().__init__(**kwargs)
        bind_attrs(self, declared_fields=declared_fields)

    def set_fields(self, fields: FieldDict):
        """Inject fields according to `declared_fields`, exclude :class:`FieldGroup`."""
        new_fields: FieldDict = {}
        # character '*' means to inject all fields
        if self.declared_fields == '*':
            for key, value in fields.items():
                if isinstance(value, Field):
                    new_fields[key] = value
        else:
            # collect and check fields
            for key in self.declared_fields:
                if key not in fields:
                    raise ValueError(f'The field "{key}" is not found.')
                value = fields[key]
                if not isinstance(value, Field):
                    raise TypeError(f'The field "{key}" must be a Field instance, not "{value}".')
                new_fields[key] = value
        self.fields = new_fields

    def set_dump(self, func: Callable = None, obj_name='group', **kwargs):
        """Override :meth:`FieldGroup.dump` method.
        See :meth:`FieldGroup.override_method` for more details.
        """
        return self.override_method(func, 'dump', obj_name, **kwargs)

    def set_load(self, func: Callable = None, obj_name='group', **kwargs):
        """Override :meth:`FieldGroup.load` method.
        See :meth:`FieldGroup.override_method` for more details.
        """
        return self.override_method(func, 'load', obj_name, **kwargs)

    def dump(self, data: dict, original_data=None):
        """Serialize multiple fields of the data."""
        return data

    def load(self, data: dict, original_data=None):
        """Deserialize multiple fields of the data."""
        return data


class CompareFields(FieldGroup):
    """Compare the values of two fields.

    :param a: The name of field on the left of the comparison operator.
    :param b: The name of field on the right of the comparison operator.
    :param op: The string of comparison operator, which must be a key in
        `CompareFields.comparison_dict`.
    :param kwargs: Same as :class:`FieldGroup`.
    """
    no_dump = True
    error_messages = {
        '>': '"{a}" must be greater than "{b}".',
        '<': '"{a}" must be less than "{b}".',
        '>=': '"{a}" must be greater than and equal to "{b}".',
        '<=': '"{a}" must be less than and equal to "{b}".',
        '==': '"{a}" must be equal to "{b}".',
        '!=': '"{a}" must not be equal to "{b}".',
    }
    comparison_dict = {
        '>': lambda a, b: a > b,
        '<': lambda a, b: a < b,
        '>=': lambda a, b: a >= b,
        '<=': lambda a, b: a <= b,
        '==': lambda a, b: a == b,
        '!=': lambda a, b: a != b,
    }
    field_a: Field
    field_b: Field

    def __init__(self, a: str, op: str, b: str, **kwargs):
        if op not in self.comparison_dict:
            raise ValueError(
                f'Argument "op" must be one of {list(self.comparison_dict)}, not "{op}".')
        self.compare = self.comparison_dict[op]
        self.op = op
        self.a = a
        self.b = b
        super().__init__(declared_fields=(a, b), **kwargs)

    def set_fields(self, fields: FieldDict):
        """After fields are injected, bind them to ``self.field_a`` and ``self.field_b``,
        format error messages, and create validate functions."""
        super().set_fields(fields)
        # bind fields to attrs
        for attr in ('a', 'b'):
            setattr(self, f'field_{attr}', self.fields[getattr(self, attr)])
        # get error messages
        dump_error = self.error_cls(self.get_error_message(
            self.op, a=self.field_a.dump_source, b=self.field_b.dump_source))
        load_error = self.error_cls(self.get_error_message(
            self.op, a=self.field_a.load_source, b=self.field_b.load_source))
        # set partial arguments for `validate`
        self.validate_dump = partial(
            self.validate,
            a_key=self.field_a.dump_target,
            b_key=self.field_b.dump_target,
            error=dump_error)
        self.validate_load = partial(
            self.validate,
            a_key=self.field_a.load_target,
            b_key=self.field_b.load_target,
            error=load_error)

    def validate(self, data: dict, a_key, b_key, error):
        a, b = data.get(a_key), data.get(b_key)
        if a is not None and b is not None and not self.compare(a, b):
            raise error

    def load(self, data: dict, original_data=None):
        self.validate_load(data)
        return data

    def dump(self, data: dict, original_data=None):
        self.validate_dump(data)
        return data


class TransformNested(FieldGroup):
    """Convert flat data to and from nested data.

    :param nested: The field name of NestedField.
    :param dump_method: The method name to dump data,
        choose one of ``'nested_to_flat'``, ``'flat_to_nested'`` to handle data.
        The default value is ``'nested_to_flat'``.
    :param load_method: The method name to load data,
        choose one of ``'nested_to_flat'``, ``'flat_to_nested'`` to handle data.
        The default value is ``'flat_to_nested'``.
    :param kwargs: Same as :class:`FieldGroup`.
    """
    nested_field: NestedField
    dump_method = 'nested_to_flat'
    load_method = 'flat_to_nested'

    def __init__(self, nested: str, dump_method: str = None, load_method: str = None, **kwargs):
        self.nested = nested
        super().__init__(declared_fields=(nested,), **kwargs)
        bind_attrs(self, dump_method=dump_method, load_method=load_method)

    def set_fields(self, fields: FieldDict):
        """Set ``self.nested_field``, and create partial load and dump methods."""
        super().set_fields(fields)
        nested_field: NestedField = self.fields[self.nested]
        if not isinstance(nested_field, NestedField):
            raise TypeError(
                f'The field "{self.nested}" must be a NestedField instance, not "{nested_field}".')
        if nested_field.many:
            raise ValueError(f'The field "{self.nested}" can not be set as "many=True".')
        self.nested_field = nested_field
        # create partial methods
        self._do_dump = partial(
            getattr(self, self.dump_method),
            target=nested_field.dump_target,
            method=nested_field.dump,
        )
        self._do_load = partial(
            getattr(self, self.load_method),
            target=nested_field.load_target,
            method=nested_field.load,
        )

    def flat_to_nested(self, data: dict, original_data, target, method):
        """Collect fields from the flat data, and set them to a nested field."""
        data[target] = method(original_data)
        return data

    def nested_to_flat(self, data: dict, target: str, **kwargs):
        """Update the flat data with the nested data."""
        data.update(data.pop(target, {}))
        return data

    def dump(self, data: dict, original_data=None):
        return self._do_dump(data=data, original_data=original_data)

    def load(self, data: dict, original_data=None):
        return self._do_load(data=data, original_data=original_data)


class SumFields(FieldGroup):
    """Calculate the sum of values of the fields.

    :param result_field: A field to convert the sum result. If None, don't convert the sum.
    :param declared_fields: The name of fields which to collect values from data.
    :param kwargs: Same as :class:`FieldGroup`.
    """
    dump_data_keys: Iterable[str]
    load_data_keys: Iterable[str]

    def __init__(self, result_field: Field = None, **kwargs):
        if result_field and not isinstance(result_field, Field):
            raise TypeError(
                f'Argument "result_field" must be a Field instance, not "{result_field}".')
        self.result_field = result_field
        super().__init__(**kwargs)

    def set_fields(self, fields: FieldDict):
        """Check if the injected fields are :class:`NumberField`."""
        super().set_fields(fields)
        for key, value in self.fields.items():
            if not isinstance(value, NumberField):
                raise TypeError(
                    f'The field "{key}" must be a NumberField instance, not "{value}".')
        # collect data keys from fields
        self.dump_data_keys = tuple(field.dump_target for field in self.fields.values())
        self.load_data_keys = tuple(field.load_target for field in self.fields.values())

    def iter_data(self, data: dict, data_keys: Iterable):
        for key in data_keys:
            value = data.get(key)
            if value is not None:
                yield value

    def dump(self, data: dict, original_data=None):
        total = sum(self.iter_data(data, self.dump_data_keys))
        if self.result_field:
            total = self.result_field.dump(total)
        data[self.dump_target] = total
        return data

    def load(self, data: dict, original_data=None):
        total = sum(self.iter_data(data, self.load_data_keys))
        if self.result_field:
            total = self.result_field.load(total)
        data[self.load_target] = total
        return data

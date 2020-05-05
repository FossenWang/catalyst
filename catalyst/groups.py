from typing import Callable, Iterable

from .fields import BaseField, Field, FieldDict
from .utils import copy_keys, bind_attrs


class FieldGroup(BaseField):
    """Field group."""
    fields: FieldDict
    declared_fields: Iterable[str] = tuple()

    def __init__(self, declared_fields: Iterable[str] = None, **kwargs):
        super().__init__(**kwargs)
        bind_attrs(self, declared_fields=declared_fields)

    def set_fields(self, fields: FieldDict):
        new_fields = {}
        fields = copy_keys(fields, self.declared_fields)
        for name, value in fields.items():
            if not isinstance(value, Field):
                raise TypeError(f'The value of fields must be an instance of Field, not {value}.')
            new_fields[name] = value
        self.fields = new_fields

    def set_dump(self, func: Callable = None, **kwargs):
        return self.override_method(func, 'dump', **kwargs)

    def set_load(self, func: Callable = None, **kwargs):
        return self.override_method(func, 'load', **kwargs)

    def dump(self, data, original_data=None):
        return data

    def load(self, data, original_data=None):
        return data


class ComparisonFieldGroup(FieldGroup):
    """Compare the values of two fields."""
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
                f'Argument `op` must be one of '
                f"{list(self.comparison_dict.keys())}, not '{op}'.")
        self.compare = self.comparison_dict[op]
        self.op = op
        self.a = a
        self.b = b
        super().__init__(declared_fields=(a, b), **kwargs)

    def set_fields(self, fields: FieldDict):
        """After fields are injected, bind them to `self.field_a` and `self.field_b`."""
        super().set_fields(fields)
        for attr in ('a', 'b'):
            key = getattr(self, attr)
            if key not in self.fields:
                raise ValueError(f'The field "{key}" not found.')
            field = self.fields[key]
            setattr(self, f'field_{attr}', field)

    def load(self, data, original_data=None):
        a, b = data.get(self.field_a.name), data.get(self.field_b.name)
        if a is not None and b is not None and not self.compare(a, b):
            self.error(self.op, a=self.field_a.key, b=self.field_b.key)
        return data

    def dump(self, data, original_data=None):
        a, b = data.get(self.field_a.key), data.get(self.field_b.key)
        if a is not None and b is not None and not self.compare(a, b):
            self.error(self.op, a=self.field_a.name, b=self.field_b.name)
        return data


# Aliases
Comparison = ComparisonFieldGroup

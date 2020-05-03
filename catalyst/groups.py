from typing import Callable

from .fields import BaseField, Field, FieldDict
from .utils import copy_keys, bind_attrs


class FieldGroup(BaseField):
    fields: FieldDict
    declared_fields = []

    def __init__(self, declared_fields: list = None, **kwargs):
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

    def __init__(self, a, op, b, **kwargs):
        if op not in self.comparison_dict:
            raise ValueError(
                f'Argument `op` must be one of '
                f"{list(self.comparison_dict.keys())}, not '{op}'.")
        self.compare = self.comparison_dict.get(op)
        self.op = op
        self.a: Field = a
        self.b: Field = b
        declared_fields = [name for name in (a, b) if not isinstance(name, Field)]
        super().__init__(declared_fields=declared_fields, **kwargs)

    def set_fields(self, fields: FieldDict):
        super().set_fields(fields)
        for attr in ('a', 'b'):
            value = getattr(self, attr)
            if value not in self.fields:
                raise ValueError(f'The field "{value}" not found.')
            setattr(self, attr, self.fields[value])

    def load(self, data, original_data=None):
        a, b = data.get(self.a.load_target), data.get(self.b.load_target)
        if a is not None and b is not None and not self.compare(a, b):
            self.error(self.op, a=self.a.load_source, b=self.b.load_source)
        return data

    def dump(self, data, original_data=None):
        a, b = data.get(self.a.dump_target), data.get(self.b.dump_target)
        if a is not None and b is not None and not self.compare(a, b):
            self.error(self.op, a=self.a.dump_source, b=self.b.dump_source)
        return data


# Aliases
Comparison = ComparisonFieldGroup

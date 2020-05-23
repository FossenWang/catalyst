from typing import Callable, Iterable
from functools import partial

from .fields import BaseField, Field, FieldDict
from .utils import bind_attrs


class FieldGroup(BaseField):
    """Field group."""
    fields: FieldDict
    declared_fields: Iterable[str] = tuple()

    def __init__(self, declared_fields: Iterable[str] = None, **kwargs):
        super().__init__(**kwargs)
        bind_attrs(self, declared_fields=declared_fields)

    def set_fields(self, fields: FieldDict):
        """Inject fields according to `declared_fields`."""
        new_fields = {}
        for key in self.declared_fields:
            if key not in fields:
                raise ValueError(f'The field "{key}" is not found.')
            value = fields[key]
            if not isinstance(value, Field):
                raise TypeError(
                    f'The field "{key}" must be an instance of Field, not "{value}".')
            new_fields[key] = value
        self.fields: FieldDict = new_fields

    def set_dump(self, func: Callable = None, **kwargs):
        return self.override_method(func, 'dump', **kwargs)

    def set_load(self, func: Callable = None, **kwargs):
        return self.override_method(func, 'load', **kwargs)

    def dump(self, data, original_data=None):
        return data

    def load(self, data, original_data=None):
        return data


class CompareFields(FieldGroup):
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
        """After fields are injected, bind them to `self.field_a` and `self.field_b`,
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

    def validate(self, data, a_key, b_key, error):
        a, b = data.get(a_key), data.get(b_key)
        if a is not None and b is not None and not self.compare(a, b):
            raise error

    def load(self, data, original_data=None):
        self.validate_load(data)
        return data

    def dump(self, data, original_data=None):
        self.validate_dump(data)
        return data

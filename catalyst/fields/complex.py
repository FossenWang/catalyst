from typing import Iterable, Callable as CallableType

from ..base import CatalystABC
from ..utils import BaseResult, copy_keys, bind_attrs
from ..validators import LengthValidator
from ..exceptions import ValidationError, ExceptionType

from .base import Field
from .simple import StringField


class ListField(Field):
    """List field, handle list elements with another `Field`.
    In order to ensure proper data structure, `None` is not valid.

    :param item_field: A `Field` class or instance.
    :param min_length: The minimum length of the list.
    :param max_length: The maximum length of the list.
    :param all_errors: Whether to collect errors for every list elements.
    :param except_exception: Which types of errors should be collected.
    :param error_messages: Keys {'too_small', 'too_large', 'not_between', ...}.
    """
    item_field: Field = None
    all_errors = True
    except_exception = Exception
    allow_none = False

    def __init__(
            self,
            item_field: Field = None,
            min_length: int = None,
            max_length: int = None,
            all_errors: bool = None,
            except_exception=None,
            **kwargs):
        super().__init__(**kwargs)
        bind_attrs(
            self,
            item_field=item_field,
            all_errors=all_errors,
            except_exception=except_exception,
        )
        if min_length is not None or max_length is not None:
            msg_dict = copy_keys(self.error_messages, ('too_small', 'too_large', 'not_between'))
            self.add_validator(LengthValidator(min_length, max_length, msg_dict))

        item_field = self.item_field
        if not isinstance(item_field, Field):
            raise TypeError(f'Argument "item_field" must be a Field instance, not "{item_field}".')
        self.format_item = getattr(item_field, 'dump')
        self.parse_item = getattr(item_field, 'load')

    def format(self, value):
        return self._process_many(
            value, self.all_errors, self.format_item, self.except_exception)

    def parse(self, value):
        return self._process_many(
            value, self.all_errors, self.parse_item, self.except_exception)

    @staticmethod
    def _process_many(
            data: Iterable,
            all_errors: bool,
            process_one: CallableType,
            except_exception: ExceptionType):
        valid_data, errors, invalid_data = [], {}, {}
        for i, item in enumerate(data):
            try:
                result = process_one(item)
                valid_data.append(result)
            except except_exception as e:
                if isinstance(e, ValidationError) and isinstance(e.detail, BaseResult):
                    # distribute nested data in BaseResult
                    valid_data.append(e.detail.valid_data)
                    errors[i] = e.detail.errors
                    invalid_data[i] = e.detail.invalid_data
                else:
                    errors[i] = e
                    invalid_data[i] = item
                if not all_errors:
                    break
        if errors:
            result = BaseResult(valid_data, errors, invalid_data)
            raise ValidationError(msg=result.format_errors(), detail=result)
        return valid_data


class SeparatedField(ListField):
    """Field for convert between a separated string and a list of the words.

    :param separator: Argument for `str.split(sep=separator)` and `separator.join`.
        If separator is `None`, whitespace will be used to join words.
        By default, separator is `,`.
    :param maxsplit: Argument for `str.split(maxsplit=maxsplit)`.
    """
    item_field: Field = StringField()
    separator = ','
    maxsplit = -1

    def __init__(
            self,
            item_field: Field = None,
            separator: str = ...,
            maxsplit: int = None,
            **kwargs):
        super().__init__(item_field=item_field, **kwargs)
        bind_attrs(self, maxsplit=maxsplit)
        if separator is not ...:  # `None` is a valid value
            self.separator = separator

    def parse(self, value):
        value = str(value).split(self.separator, self.maxsplit)
        value = super().parse(value)
        return value

    def format(self, value):
        value = super().format(value)
        separator = self.separator or ' '
        value = separator.join(str(v) for v in value)
        return value


class NestedField(Field):
    """Nested field, handle one or more objects with `Catalyst`.
    In order to ensure proper data structure, `None` is not valid.

    :param Catalyst catalyst: A `Catalyst` class or instance.
    :param many: Whether to process multiple objects.
    """
    catalyst: CatalystABC = None
    many = False
    allow_none = False

    def __init__(self, catalyst: CatalystABC = None, many: bool = None, **kwargs):
        super().__init__(**kwargs)
        bind_attrs(self, catalyst=catalyst, many=many)

        catalyst = self.catalyst
        if not isinstance(catalyst, CatalystABC):
            raise TypeError(f'Argument "catalyst" must be a Catalyst instance, not "{catalyst}".')
        if self.many:
            self._do_dump = catalyst.dump_many
            self._do_load = catalyst.load_many
        else:
            self._do_dump = catalyst.dump
            self._do_load = catalyst.load

    def format(self, value):
        return self._do_dump(value, raise_error=True).valid_data

    def parse(self, value):
        return self._do_load(value, raise_error=True).valid_data

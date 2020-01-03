from typing import Sequence, Callable
from functools import partial

from .utils import LoadResult, DumpResult, BaseResult
from .exceptions import ValidationError


class CatalystPacker:
    raise_error = False
    all_errors = True

    def __init__(
            self,
            catalysts: Sequence = None,
            raise_error: bool = None,
            all_errors: bool = None):
        self.catalysts = [] if catalysts is None else catalysts
        if raise_error is not None:
            self.raise_error = raise_error
        if all_errors is not None:
            self.all_errors = all_errors

        # make processors when initializing for shorter run time
        self._do_dump = self._make_processor('dump', False)
        self._do_load = self._make_processor('load', False)
        self._do_dump_many = self._make_processor('dump', True)
        self._do_load_many = self._make_processor('load', True)

    @staticmethod
    def _process_one(data: Sequence, all_errors: bool, processors: Sequence[Callable]):
        valid_data, errors, invalid_data = {}, {}, {}
        for processor, item in zip(processors, data):
            result = processor(item, raise_error=False, all_errors=all_errors)
            if result.is_valid:
                valid_data.update(result.valid_data)
            else:
                errors.update(result.errors)
                invalid_data.update(result.invalid_data)
                if not all_errors:
                    break
        return valid_data, errors, invalid_data

    @staticmethod
    def _process_many(data: Sequence[Sequence], all_errors: bool, process_one: Callable):
        valid_data, errors, invalid_data = [], {}, {}
        for i, items in enumerate(zip(*data)):
            result = process_one(items, raise_error=False, all_errors=all_errors)
            valid_data.append(result.valid_data)
            if not result.is_valid:
                errors[i] = result.errors
                invalid_data[i] = result.invalid_data
                if not all_errors:
                    break
        return valid_data, errors, invalid_data

    def _make_processor(self, name: str, many: bool) -> Callable:
        if name == 'dump':
            ResultClass = DumpResult
        elif name == 'load':
            ResultClass = LoadResult
        else:
            raise ValueError("Argment 'name' must be 'dump' or 'load'.")

        if many:
            process_one = getattr(self, name)
            main_process = partial(self._process_many, process_one=process_one)
        else:
            processors = [getattr(catalyst, name) for catalyst in self.catalysts]
            main_process = partial(self._process_one, processors=processors)

        default_raise_error = self.raise_error
        default_all_errors = self.all_errors

        def integrated_process(data, raise_error, all_errors):
            if raise_error is None:
                raise_error = default_raise_error
            if all_errors is None:
                all_errors = default_all_errors

            valid_data, errors, invalid_data = main_process(data, all_errors)

            result = ResultClass(valid_data, errors, invalid_data)
            if errors and raise_error:
                raise ValidationError(result)
            return result

        return integrated_process

    def dump(
            self,
            data: Sequence,
            raise_error: bool = None,
            all_errors: bool = None,
        ) -> DumpResult:
        return self._do_dump(data, raise_error, all_errors)

    def load(
            self,
            data: Sequence,
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

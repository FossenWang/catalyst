from typing import Iterable, Callable
from functools import partial

from .utils import LoadResult, DumpResult, bind_attrs
from .exceptions import ValidationError


class CatalystPacker:
    catalysts = []
    raise_error = False
    all_errors = True

    def __init__(
            self,
            catalysts: Iterable = None,
            raise_error: bool = None,
            all_errors: bool = None):
        bind_attrs(
            self,
            catalysts=catalysts,
            raise_error=raise_error,
            all_errors=all_errors,
        )

        # make processors when initializing for shorter run time
        self._do_dump = self._make_processor('dump', False)
        self._do_load = self._make_processor('load', False)
        self._do_dump_many = self._make_processor('dump', True)
        self._do_load_many = self._make_processor('load', True)

    @staticmethod
    def _process_one(data: Iterable, all_errors: bool, processors: Iterable[Callable]):
        valid_data, errors, invalid_data = {}, {}, {}
        for processor, item in zip(processors, data):
            result = processor(item, raise_error=False)
            if result.is_valid:
                valid_data.update(result.valid_data)
            else:
                errors.update(result.errors)
                invalid_data.update(result.invalid_data)
                if not all_errors:
                    break
        return valid_data, errors, invalid_data

    @staticmethod
    def _process_many(data: Iterable[Iterable], all_errors: bool, process_one: Callable):
        valid_data, errors, invalid_data = [], {}, {}
        for i, items in enumerate(zip(*data)):
            result = process_one(items, raise_error=False)
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
            raise ValueError('Argment "name" must be "dump" or "load".')

        all_errors = self.all_errors
        if many:
            process_one = getattr(self, name)
            main_process = partial(
                self._process_many,
                all_errors=all_errors,
                process_one=process_one)
        else:
            processors = [getattr(catalyst, name) for catalyst in self.catalysts]
            main_process = partial(
                self._process_one,
                all_errors=all_errors,
                processors=processors)

        default_raise_error = self.raise_error

        def integrated_process(data, raise_error):
            if raise_error is None:
                raise_error = default_raise_error

            valid_data, errors, invalid_data = main_process(data)

            result = ResultClass(valid_data, errors, invalid_data)
            if errors and raise_error:
                raise ValidationError(result)
            return result

        return integrated_process

    def dump(self, data: Iterable, raise_error: bool = None) -> DumpResult:
        return self._do_dump(data, raise_error)

    def load(self, data: Iterable, raise_error: bool = None) -> LoadResult:
        return self._do_load(data, raise_error)

    def dump_many(self, data: Iterable, raise_error: bool = None) -> DumpResult:
        return self._do_dump_many(data, raise_error)

    def load_many(self, data: Iterable, raise_error: bool = None) -> LoadResult:
        return self._do_load_many(data, raise_error)

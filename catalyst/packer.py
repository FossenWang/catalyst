from typing import Sequence

from .utils import LoadResult, DumpResult, CatalystResult
from .exceptions import ValidationError


class CatalystPacker:
    raise_error = False
    all_errors = True

    def __init__(self,
                 catalysts: Sequence = None,
                 raise_error: bool = None,
                 all_errors: bool = None,
                 ):
        self.catalysts = [] if catalysts is None else catalysts
        if raise_error is not None:
            self.raise_error = raise_error
        if all_errors is not None:
            self.all_errors = all_errors

    def _process_flow(self,
                      name: str,
                      data: Sequence,
                      raise_error: bool = None,
                      all_errors: bool = None,
                      ) -> CatalystResult:
        if name == 'dump':
            ResultClass = DumpResult
        elif name == 'load':
            ResultClass = LoadResult
        else:
            raise ValueError("Argment 'name' must be 'dump' or 'load'.")

        if raise_error is None:
            raise_error = self.raise_error
        if all_errors is None:
            all_errors = self.all_errors

        valid_data, errors, invalid_data = {}, {}, {}
        for catalyst, item in zip(self.catalysts, data):
            result = catalyst._process_flow(name, False, item, False, all_errors)
            if result.is_valid:
                valid_data.update(result.valid_data)
            else:
                errors.update(result.errors)
                invalid_data.update(result.invalid_data)
                if not all_errors:
                    break

        result = ResultClass(valid_data, errors, invalid_data)
        if errors and raise_error:
            raise ValidationError(result)
        return result

    def dump(self,
             data: Sequence,
             raise_error: bool = None,
             all_errors: bool = None,
             ) -> DumpResult:
        return self._process_flow('dump', data, raise_error, all_errors)

    def load(self,
             data: Sequence,
             raise_error: bool = None,
             all_errors: bool = None,
             ) -> LoadResult:
        return self._process_flow('load', data, raise_error, all_errors)

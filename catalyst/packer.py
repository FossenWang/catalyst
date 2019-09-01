from .utils import LoadResult, DumpResult, CatalystResult


class CatalystPacker:
    def __init__(self):
        self.packages = []

    def pack(self, catalyst, data):
        self.packages.append((catalyst, data))
        return self

    def _base_handle(self,
                     name: str,
                     raise_error: bool = None,
                     all_errors: bool = None,
                     ) -> CatalystResult:
        if name == 'dump':
            ResultClass = DumpResult
        elif name == 'load':
            ResultClass = LoadResult
        else:
            raise ValueError("Argment 'name' must be 'dump' or 'load'.")

        valid_data, errors, invalid_data = {}, {}, {}
        for catalyst, data in self.packages:
            temp = catalyst._base_handle(data, name, raise_error, all_errors)
            valid_data.update(temp.valid_data)
            errors.update(temp.errors)
            invalid_data.update(temp.invalid_data)
        result = ResultClass(valid_data, errors, invalid_data)
        return result

    def dump(self,
             raise_error: bool = None,
             all_errors: bool = None,
             ) -> DumpResult:
        return self._base_handle('dump', raise_error, all_errors)

    def load(self,
             raise_error: bool = None,
             all_errors: bool = None,
             ) -> LoadResult:
        return self._base_handle('load', raise_error, all_errors)

    def clear(self):
        self.packages.clear()

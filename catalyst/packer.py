from .utils import LoadResult, DumpResult


class CatalystPacker:
    def __init__(self):
        self.packages = []

    def pack(self, catalyst, data):
        self.packages.append((catalyst, data))
        return self

    def dump(self,
             raise_error: bool = None,
             all_errors: bool = None
             ) -> DumpResult:
        valid_data, errors, invalid_data = {}, {}, {}
        for catalyst, data in self.packages:
            temp = catalyst.dump(data, raise_error, all_errors)
            valid_data.update(temp.valid_data)
            errors.update(temp.errors)
            invalid_data.update(temp.invalid_data)
        result = DumpResult(valid_data, errors, invalid_data)
        return result

    def load(self,
             raise_error: bool = None,
             all_errors: bool = None
             ) -> LoadResult:
        valid_data, errors, invalid_data = {}, {}, {}
        for catalyst, data in self.packages:
            temp = catalyst.load(data, raise_error, all_errors)
            valid_data.update(temp.valid_data)
            errors.update(temp.errors)
            invalid_data.update(temp.invalid_data)
        result = LoadResult(valid_data, errors, invalid_data)
        return result

    def clear(self):
        self.packages.clear()

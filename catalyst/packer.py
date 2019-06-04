class CatalystPacker:
    def __init__(self):
        self._packages = []

    def pack(self, catalyst, data):
        self._packages.append((catalyst, data))
        return self

    def dump(self) -> dict:
        result = {}
        for catalyst, data in self._packages:
            temp = catalyst.dump(data)
            result.update(temp)
        return result

    def load(self,
             raise_error: bool = None,
             collect_errors: bool = None
             ):
        result = {}
        for catalyst, data in self._packages:
            temp = catalyst.load(data, raise_error=raise_error, collect_errors=collect_errors)
            result.update(temp)
        return result

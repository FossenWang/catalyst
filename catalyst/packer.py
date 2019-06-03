class Packer:
    def __init__(self):
        self._packages = []

    def pack(self, catalyst, data):
        self._packages.append((catalyst, data))
        return self

    def dump(self):
        result = {}
        for catalyst, data in self._packages:
            temp = catalyst.dump(data)
            result.update(temp)
        return result

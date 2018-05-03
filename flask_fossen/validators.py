class StringValidator:

    def __call__(self, key, string):
        assert isinstance(string, str), \
        "Attribute '%s' must be <class 'str'>, not %s: %s" \
        % (key, type(string), string)
        return string


class MaxLengthValidator(StringValidator):
    def __init__(self, max_length):
        self.max_length = max_length
        self.message = 'String length must be less than %d' % max_length

    def __call__(self, key, string):
        string = super().__call__(key, string)
        assert len(string) <= self.max_length, self.message
        return string


class IntegerValidator:
    def __call__(self, key, value):
        return int(value)



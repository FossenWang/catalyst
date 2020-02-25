from typing import Union, Type, Tuple


ExceptionType = Union[Type[Exception], Tuple[Type[Exception]]]


class ValidationError(Exception):
    def __init__(self, msg, *args):
        self.msg = msg
        super().__init__(*args)

    def __repr__(self):
        return 'ValidationError(%s)' % repr(self.msg)

    def __str__(self):
        return str(self.msg)

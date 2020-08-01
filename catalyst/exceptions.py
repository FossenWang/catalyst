from typing import Union, Type, Tuple


ExceptionType = Union[Type[Exception], Tuple[Type[Exception]]]


class ValidationError(Exception):
    """Raised when validation fails on a field or catalyst.

    :param msg: An error message, list of error messages, or dict of
        error messages.
    :param detail: A `DumpResult`, `LoadResult`, or any information
        about the error detail.
    """

    def __init__(self, msg, detail=None):
        super().__init__()
        self.msg = msg
        self.detail = detail

    def __repr__(self):
        return f'ValidationError({self.msg!r})'

    def __str__(self):
        return str(self.msg)

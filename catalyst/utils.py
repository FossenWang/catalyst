from .exceptions import ValidationError


class ErrorMessageMixin:
    default_error_messages = {}

    def collect_error_messages(self, error_messages: dict = None):
        """
        Collect default error message from self and parent classes.

        :param error_messages: message dict, defaults to None
        :type error_messages: dict, optional
        """
        messages = {}
        for cls in reversed(self.__class__.__mro__):
            messages.update(getattr(cls, 'default_error_messages', {}))
        messages.update(error_messages or {})
        self.error_messages = messages

    def error(self, error_key: str):
        raise ValidationError(self.error_messages.get(error_key))

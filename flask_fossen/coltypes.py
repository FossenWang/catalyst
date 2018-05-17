from sqlalchemy.sql.sqltypes import Integer, String, Boolean


class EmailType(String):
    pass

class PasswordType(String):
    def __init__(self, min_length=None, *args, **kwargs):
        self.min_length = min_length
        super().__init__(self, *args, **kwargs)


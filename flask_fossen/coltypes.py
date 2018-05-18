from sqlalchemy.sql.sqltypes import Integer, String, Boolean, Enum


class EmailType(String):
    pass

class PasswordType(String):
    def __init__(self, *args, raw_password_length=(6, 20), special_chars=',.?;_!@#$%^&*?', **kwargs):
        self.raw_password_length = raw_password_length
        self.special_chars = special_chars
        super().__init__(*args, **kwargs)


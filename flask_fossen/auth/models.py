from sqlalchemy import Column
from werkzeug.security import generate_password_hash, check_password_hash

from ..coltypes import EmailType, PasswordType, String
from ..models import SerializableModel, IdMixin






class PasswordMixin:
    _password = Column('password', PasswordType(128), nullable=False)

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, raw):
        self._password = generate_password_hash(raw)

    def check_password(self, raw):
        if not self._password:
            return False
        return check_password_hash(self._password, raw)

'''
class User(IdMixin, SerializableModel):
    email = Column(EmailType(254), unique=True, nullable=False)
    username = Column(String(150), unique=True, nullable=False)
'''

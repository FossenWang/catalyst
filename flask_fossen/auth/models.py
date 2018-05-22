from sqlalchemy import Column
from werkzeug.security import generate_password_hash, check_password_hash

from ..coltypes import EmailType, PasswordType, String
from ..models import Model


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


class AbstractUser(PasswordMixin, Model):
    __abstract__ = True
    username = Column(String(150), unique=True, nullable=False)
    email = Column(EmailType(254), unique=True, nullable=False)

    def __str__(self):
        return self.username

    class Meta:
        serialize_ignore = ['password']


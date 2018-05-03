from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, validates

from flask_fossen.models import SerializableModel, IdMixin

class ValidationError(ValueError):
    pass

db = SQLAlchemy(model_class=SerializableModel)


class User(IdMixin, db.Model):
    name = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)

    def __str__(self):
        return self.name

    @validates('name')
    def validate_name(self, key, string):
        col = self.__mapper__.columns[key]
        assert len(string)<=col.type.length, 'str too long'
        return string

    @validates('email')
    def validate_email(self, key, address):
        assert '@' in address, 'Invalid email'
        return address

class Article(IdMixin, db.Model):
    title = Column(String(64), nullable=False)
    content = Column(String(64), nullable=False)
    author_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    author = relationship('User', backref='articles')

    def __str__(self):
        return self.title


from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from flask_fossen.models import Model, db
from flask_fossen.auth.models import AbstractUser



class User(AbstractUser):
    pass


class Article(Model):
    title = Column(String(64), nullable=False)
    content = Column(String(64), nullable=False)
    author_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    author = relationship('User', backref='articles')

    def __str__(self):
        return self.title


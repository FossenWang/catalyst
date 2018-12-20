from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from flask_fossen.models import Model
from flask_fossen.auth.models import AbstractUser



class User(AbstractUser):
    __tablename__ = 'flask_fossen_user'

class Article(Model):
    __tablename__ = 'flask_fossen_article'

    title = Column(String(64), nullable=False)
    content = Column(String(64), nullable=False)
    author_id = Column(Integer, ForeignKey('flask_fossen_user.id'), nullable=False)
    author = relationship(User, backref='articles')

    def __str__(self):
        return self.title

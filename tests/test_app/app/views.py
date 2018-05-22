from flask import Blueprint

from flask_fossen.views import Resource, ResourceList
from flask_fossen.http import register_json_error_handle
from flask_fossen.auth import auth_jwt, BaseLoginView, LogoutView, RefreshToken, BaseUserView

from .database import User, Article, db


def index():
    return 'Test.'


class ArticleView(Resource):
    model = Article
    db = db


class ArticleList(ResourceList):
    model = Article
    db = db


class LoginView(BaseLoginView):
    model = User


class UserView(BaseUserView):
    model = User
    db = db


# url config
bp = Blueprint('api', __name__, url_prefix='/api')
bp.add_url_rule('/', view_func=index)
bp.add_url_rule('/articles/<int:id>', view_func=ArticleView.as_view('article'))
bp.add_url_rule('/articles', view_func=ArticleList.as_view('article_list'))

bp.add_url_rule('/users', view_func=UserView.as_view('users'))
bp.add_url_rule('/login', view_func=LoginView.as_view('login'))
bp.add_url_rule('/logout', view_func=LogoutView.as_view('logout'))
bp.add_url_rule('/token/refresh', view_func=RefreshToken.as_view('token_refresh'))


register_json_error_handle(bp)


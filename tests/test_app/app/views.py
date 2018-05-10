from flask import Blueprint
from wtforms.ext.sqlalchemy.orm import model_form

from flask_fossen.views.rest import Resource, ResourceList
from flask_fossen.http import register_json_error_handle

from .database import User, Article, db

# ArticleForm = model_form(Article, db.session)
# af = ArticleForm(author=admin,title='tset',content='tset')
# af.validate()
# import wtforms.ext.sqlalchemy.fields.QuerySelectField


def index():
    return 'Test.'

class ArticleView(Resource):
    model = Article
    db = db

class ArticleList(ResourceList):
    model = Article
    db = db

    def pre_serialize_object_list(self, object_list, related=['author'], ignore=['author_id']):
        return super().pre_serialize_object_list(object_list, related=related, ignore=ignore)

# url config
bp = Blueprint('api', __name__, url_prefix='/api')
bp.add_url_rule('/', view_func=index)
bp.add_url_rule('/articles/<int:id>', view_func=ArticleView.as_view('article'))
bp.add_url_rule('/articles', view_func=ArticleList.as_view('article_list'))


register_json_error_handle(bp)


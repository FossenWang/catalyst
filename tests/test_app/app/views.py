from flask import Blueprint
from flask_fossen.views.rest import SingleResource
from wtforms.ext.sqlalchemy.orm import model_form

from .database import User, Article, db

# ArticleForm = model_form(Article, db.session)
# af = ArticleForm(author=admin,title='tset',content='tset')
# af.validate()
# import wtforms.ext.sqlalchemy.fields.QuerySelectField


def index():
    return 'Test.'

class ArticleView(SingleResource):
    model = Article
    db = db




# url config
bp = Blueprint('api', __name__, url_prefix='/api')
bp.add_url_rule('/', view_func=index)
bp.add_url_rule('/articles/<int:id>', view_func=ArticleView.as_view('article'))

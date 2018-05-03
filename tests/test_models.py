from flask_fossen.testcases import FlaskTestCase

from .test_app.app import create_app, db
from .test_app.app.database import User, Article


class SerializableModelTest(FlaskTestCase):
    app = create_app()
    db = db

    def setUp(self):
        self.session = self.db.session
        admin = User(name='admin', email='admin@fossen.cn')
        self.session.add(admin)
        self.session.commit()
        articles = [Article(title='article:%d'%i, content='test article:%d'%i, author=admin) for i in range(1)]
        self.session.add_all(articles)
        self.session.commit()

        self.articles = Article.query.all()
        self.admin = User.query.get(1)

    def test_to_dict_default(self):
        admin = self.admin.to_dict()
        adict = [a.to_dict() for a in self.articles]
        self.assertEqual(admin, {'id': 1, 'name': 'admin', 'email': 'admin@fossen.cn'})
        self.assertEqual(adict, [{'id': 1, 'title': 'article:0', 'content': 'test article:0', 'author_id': 1}])

    def test_to_dict_nested_related(self):
        admin = self.admin.to_dict(related=['articles:author'])
        adict = [a.to_dict(related=['author:articles']) for a in self.articles]
        self.assertEqual(admin, {'id': 1, 'name': 'admin', 'email': 'admin@fossen.cn', 'articles': [{'id': 1, 'title': 'article:0', 'content': 'test article:0', 'author_id': 1, 'author': {'id': 1, 'name': 'admin', 'email': 'admin@fossen.cn'}}]})
        self.assertEqual(adict, [{'id': 1, 'title': 'article:0', 'content': 'test article:0', 'author_id': 1, 'author': {'id': 1, 'name': 'admin', 'email': 'admin@fossen.cn', 'articles': [{'id': 1, 'title': 'article:0', 'content': 'test article:0', 'author_id': 1}]}}])

    def test_to_dict_ignore(self):
        admin = self.admin.to_dict(ignore=['id', 'articles:id'], related=['articles'])
        adict = [a.to_dict(ignore=['id', 'author:id'], related=['author']) for a in self.articles]
        self.assertEqual(admin, {'name': 'admin', 'email': 'admin@fossen.cn', 'articles': [{'title': 'article:0', 'content': 'test article:0', 'author_id': 1}]})
        self.assertEqual(adict, [{'title': 'article:0', 'content': 'test article:0', 'author_id': 1, 'author': {'name': 'admin', 'email': 'admin@fossen.cn'}}])

    def test_to_dict_nested(self):
        admin = self.admin.to_dict(ignore=['name', 'email', 'articles:title','articles:content','articles:author_id','articles:content','articles:author:name','articles:author:email'],related=['articles:author'])
        adict = [a.to_dict(ignore=['title', 'content', 'author_id', 'author:name', 'author:email'], related=['author:articles']) for a in self.articles]
        self.assertEqual(admin, {'id': 1, 'articles': [{'id': 1, 'author': {'id': 1}}]})
        self.assertEqual(adict,[{'id': 1, 'author': {'id': 1, 'articles': [{'id': 1, 'title': 'article:0', 'content': 'test article:0', 'author_id': 1}]}}])

    def test_pre_serialize(self):
        admin = self.admin.pre_serialize(ignore=['name', 'email', 'articles:title','articles:content','articles:author_id','articles:content','articles:author:name','articles:author:email'],related=['articles:author'])
        adict = Article.pre_serialize(self.articles, ignore=['title', 'content', 'author_id', 'author:name', 'author:email'], related=['author:articles'])
        self.assertEqual(admin, {'id': 1, 'articles': [{'id': 1, 'author': {'id': 1}}]})
        self.assertEqual(adict,[{'id': 1, 'author': {'id': 1, 'articles': [{'id': 1, 'title': 'article:0', 'content': 'test article:0', 'author_id': 1}]}}])
        self.assertRaises(AssertionError, Article.pre_serialize, [self.articles[0], 0])

    def test_to_json(self):
        admin = self.admin.to_json(ignore=['name', 'email', 'articles:title','articles:content','articles:author_id','articles:content','articles:author:name','articles:author:email'],related=['articles:author'])
        self.assertEqual(admin, '{"id": 1, "articles": [{"id": 1, "author": {"id": 1}}]}')

    def test_validator(self):
        u=User(name='adsadasdsa')
        print(u.name)
        self.assertRaises(AssertionError, User, email='wrong email', name='asdqwasdsdasdas'*10)


from flask_fossen.testcases import FlaskTestCase
from flask_fossen.validators import IntegerValidator, StringValidator, MaxLengthValidator

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

    def test_validate_data(self):
        invalid_data = {'name':'adsadasdsa'*20, 'email': []}
        valid, errors = User.validate_data(invalid_data)
        self.assertEqual(valid, False)
        self.assertEqual(errors, {'name': ['AssertionError: Ensure string length is less than or equal to 80'], 'email': ["AssertionError: Enter a string, not <class 'list'>"]})

        invalid_data = {'name':'adsadasdsa'*20,}
        valid, errors = User.validate_data(invalid_data)
        self.assertEqual(valid, False)
        self.assertEqual(errors, {'name': ['AssertionError: Ensure string length is less than or equal to 80'], 'email': ['ValueError: Ensure value is not None']})

        valid_data = {'name':'admin', 'email': 'admin@fossen.cn'}
        valid, errors = User.validate_data(valid_data)
        self.assertEqual(valid, True)
        self.assertEqual(errors, {})

        valid, errors = User.validate_data(self.admin.pre_serialize())
        self.assertEqual(valid, True)
        self.assertEqual(errors, {})

        invalid_data = {'email': []}
        valid, errors = Article.validate_data(invalid_data)
        self.assertEqual(valid, False)
        self.assertEqual(errors, {'email': ["TypeError: 'email' is not a field of Article"],'title': ['ValueError: Ensure value is not None'], 'content': ['ValueError: Ensure value is not None'], 'author_id': ['ValueError: Ensure value is not None']})

    def test_ValidationMeta_param(self):
        self.assertIsInstance(Article._meta.default_validators.get('id')[0], IntegerValidator)
        self.assertIsInstance(Article._meta.default_validators.get('title')[0], MaxLengthValidator)
        self.assertIsInstance(Article._meta.default_validators.get('author_id')[0], IntegerValidator)
        self.assertEqual(Article._meta.default_validators.get('author'), [])
        self.assertEqual(Article._meta.required_fields, ['title', 'content', 'author_id'])
        self.assertEqual(hasattr(Article._meta, 'extra_validators'), False)
    
        class A1(Article):
            class Meta:
                default_validators = {'id': [IntegerValidator()], 'title': [StringValidator()]}
                extra_validators = {'title': [MaxLengthValidator]}
                required_fields = ['title']
        self.assertIsInstance(A1._meta.default_validators.get('id')[0], IntegerValidator)
        self.assertIsInstance(A1._meta.default_validators.get('title')[0], StringValidator)
        self.assertEqual(A1._meta.required_fields, ['title'])
        self.assertEqual(hasattr(A1._meta, 'extra_validators'), True)

    def test_create_and_update_object(self):
        valid_data = {'title':'Fossen is awesome!', 'content':'Fossen is awesome!', 'author_id':1}
        valid, errors = Article.validate_data(valid_data)
        self.assertEqual(valid, True)
        self.assertEqual(errors, {})
        a = Article.create(valid_data)
        self.assertIsInstance(a, Article)
        self.assertEqual(a.pre_serialize(), {'id': None, 'title':'Fossen is awesome!', 'content':'Fossen is awesome!', 'author_id':1})

        a = self.articles[0]
        old_value = a.pre_serialize()
        Article.update(a, {'title':'Fossen is awesome!', 'content':'Fossen is awesome!', 'author_id':1})
        new_value = a.pre_serialize()
        self.assertNotEqual(old_value, new_value)
        self.assertEqual(new_value, {'id': 1, 'title': 'Fossen is awesome!', 'content': 'Fossen is awesome!', 'author_id': 1})

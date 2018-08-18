import json
from flask_fossen.testcases import FlaskTestCase
from flask_fossen.validators import IntegerValidator, MaxLengthValidator

from .test_app.app import create_app, db
from .test_app.app.database import User, Article


class SerializableModelTest(FlaskTestCase):
    app = create_app()
    db = db

    def setUp(self):
        self.session = self.db.session
        admin = User(username='admin', email='admin@test.com',
                     password='asd123')
        self.session.add(admin)
        self.session.commit()
        articles = [Article(title='article:%d' % i, content='test article:%d' %
                            i, author=admin) for i in range(1)]
        self.session.add_all(articles)
        self.session.commit()

        self.articles = Article.query.all()
        self.admin = User.query.get(1)

    def test_serializable_model(self):
        # test to_dict default
        admin = self.admin.to_dict(ignore=['password'])
        adict = [a.to_dict() for a in self.articles]
        self.assertEqual(
            admin, {'id': 1, 'username': 'admin', 'email': 'admin@test.com'})
        self.assertEqual(adict, [{'id': 1, 'title': 'article:0', 'content': 'test article:0', 'author_id': 1}])

        # test to_dict None related
        a = Article(title='title', content='content')
        adict = a.to_dict(related=['author:articles'])
        self.assertEqual(adict['author'], None)
        u = User(username='user', email='user@fossen.cn').to_dict(
            related=['articles'])
        self.assertEqual(u['articles'], [])

        # test to_dict nested related
        admin = self.admin.to_dict(related=['articles:author'], ignore=['password', 'articles:author:password'])
        adict = [a.to_dict(related=['author:articles'], ignore=['author:password']) for a in self.articles]
        self.assertEqual(admin, {'id': 1, 'username': 'admin', 'email': 'admin@test.com', 'articles': [{'id': 1, 'title': 'article:0', 'content': 'test article:0', 'author_id': 1, 'author': {'id': 1, 'username': 'admin', 'email': 'admin@test.com'}}]})
        self.assertEqual(adict, [{'id': 1, 'title': 'article:0', 'content': 'test article:0', 'author_id': 1, 'author': {'id': 1, 'username': 'admin', 'email': 'admin@test.com', 'articles': [{'id': 1, 'title': 'article:0', 'content': 'test article:0', 'author_id': 1}]}}])

        # test to_dict ignore
        admin = self.admin.to_dict(ignore=['id', 'articles:id', 'password'], related=['articles'])
        adict = [a.to_dict(ignore=['id', 'author:id', 'author:password'], related=['author']) for a in self.articles]
        self.assertEqual(admin, {'username': 'admin', 'email': 'admin@test.com', 'articles': [{'title': 'article:0', 'content': 'test article:0', 'author_id': 1}]})
        self.assertEqual(adict, [{'title': 'article:0', 'content': 'test article:0', 'author_id': 1, 'author': {'username': 'admin', 'email': 'admin@test.com'}}])

        # test to_dict nested
        admin = self.admin.to_dict(ignore=['username', 'email', 'password', 'articles:title', 'articles:content', 'articles:author_id', 'articles:content', 'articles:author:username', 'articles:author:email', 'articles:author:password'], related=['articles:author'])
        adict = [a.to_dict(ignore=['title', 'content', 'author_id', 'author:username', 'author:email', 'author:password'], related=['author:articles']) for a in self.articles]
        self.assertEqual(admin, {'id': 1, 'articles': [{'id': 1, 'author': {'id': 1}}]})
        self.assertEqual(adict, [{'id': 1, 'author': {'id': 1, 'articles': [{'id': 1, 'title': 'article:0', 'content': 'test article:0', 'author_id': 1}]}}])

        # test serialize
        admin = self.admin.serialize(ignore=['username', 'email', 'password', 'articles:title', 'articles:content', 'articles:author_id', 'articles:content', 'articles:author:username', 'articles:author:email', 'articles:author:password'], related=['articles:author'])
        adict = Article.serialize(self.articles, ignore=['title', 'content', 'author_id', 'author:username', 'author:email', 'author:password'], related=['author:articles'])
        self.assertEqual(admin, {'id': 1, 'articles': [{'id': 1, 'author': {'id': 1}}]})
        self.assertEqual(adict, [{'id': 1, 'author': {'id': 1, 'articles': [{'id': 1, 'title': 'article:0', 'content': 'test article:0', 'author_id': 1}]}}])
        self.assertRaises(AssertionError, Article.serialize,
                          [self.articles[0], 0])

        # test to_json
        admin = self.admin.to_json(ignore=['username', 'email', 'password', 'articles:title', 'articles:content', 'articles:author_id', 'articles:content', 'articles:author:username', 'articles:author:email', 'articles:author:password'], related=['articles:author'])
        self.assertEqual(admin, json.dumps(
            {"id": 1, "articles": [{"id": 1, "author": {"id": 1}}]}))

        # test Meta serialization options
        class A(Article):
            class Meta:
                serialize_related = ['author']
                serialize_ignore = ['id', 'author_id', 'author:id', 'author:password']
                serialize_formatting = {'title': lambda v: v[:-2]}
        data = [A(title='article:%d' % i, content='test article:%d' %
                  i, author_id=1, author=self.admin) for i in range(1)]
        results = A.serialize(data)
        self.assertEqual(results, [{'title': 'article', 'content': 'test article:0', 'author': {'username': 'admin', 'email': 'admin@test.com'}}])

        # test validate data
        invalid_data = {'username': 'adsadasdsa'*16, 'email': []}
        result = User.validate_data(invalid_data)
        self.assertEqual(result.is_valid, False)
        self.assertEqual(result.errors, {'username': ['Ensure string length is less than or equal to 150'], 'email': ['Enter a valid email address']})

        valid_data = {'username': 'admin', 'email': 'admin@test.com', 'password': 'asd123'}
        result = User.validate_data(valid_data)
        self.assertEqual(result.is_valid, True)
        self.assertEqual(result.errors, {})

        data = self.admin.serialize()
        data.update({'password': 'asd123'})
        result = User.validate_data(data)
        self.assertEqual(result.is_valid, True)
        self.assertEqual(result.errors, {})

        invalid_data = {'email': []}
        result = Article.validate_data(invalid_data)
        self.assertEqual(result.is_valid, False)
        self.assertEqual(result.errors, {'title': ['Ensure value is not None'], 'content': ['Ensure value is not None'], 'author_id': ['Ensure value is not None']})

        # test ValidationMeta param
        self.assertIsInstance(Article._meta.default_validators.get('id')[0], IntegerValidator)
        self.assertIsInstance(Article._meta.default_validators.get( 'title')[0], MaxLengthValidator)
        self.assertIsInstance(Article._meta.default_validators.get( 'author_id')[0], IntegerValidator)
        self.assertEqual(Article._meta.default_validators.get('author'), [])
        self.assertEqual(Article._meta.required_fields, ['title', 'content', 'author_id'])
        self.assertEqual(hasattr(Article._meta, 'extra_validators'), False)

        class A1(Article):
            class Meta:
                default_validators = {'id': [MaxLengthValidator(50)]}
                extra_validators = {'title': [IntegerValidator()]}
                required_fields = ['title']
        self.assertIsInstance(A1._meta.default_validators.get('id')[0], MaxLengthValidator)
        self.assertIsInstance(A1._meta.default_validators.get('title')[1], IntegerValidator)
        self.assertEqual(A1._meta.required_fields, ['title'])
        self.assertTrue(hasattr(A1._meta, 'extra_validators'))
        self.assertTrue('author' in A1._meta.default_validators)

        # test create and update object
        valid_data = {'title': 'Fossen is awesome!', 'content': 'Fossen is awesome!', 'author_id': 1}
        result = Article.validate_data(valid_data)
        self.assertEqual(result.is_valid, True)
        self.assertEqual(result.errors, {})
        a = Article.create(valid_data)
        self.assertIsInstance(a, Article)
        self.assertEqual(a.serialize(), {'id': None, 'title': 'Fossen is awesome!', 'content': 'Fossen is awesome!', 'author_id': 1})

        a = self.articles[0]
        old_value = a.serialize()
        Article.update(a, {'title': 'Fossen is awesome!', 'content': 'Fossen is awesome!', 'author_id': 1})
        new_value = a.serialize()
        self.assertNotEqual(old_value, new_value)
        self.assertEqual(new_value, {'id': 1, 'title': 'Fossen is awesome!', 'content': 'Fossen is awesome!', 'author_id': 1})

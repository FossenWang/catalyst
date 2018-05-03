from flask_fossen.testcases import FlaskTestCase

from .test_app.app import create_app, db
from .test_app.app.database import User, Article


class ViewTest(FlaskTestCase):
    app = create_app()
    db = db

    def setUp(self):
        self.session = self.db.session
        self.admin = User(name='admin', email='admin@fossen.cn')
        self.session.add(self.admin)
        self.session.commit()
        self.articles = [Article(title='article:%d'%i, content='test article:%d'%i, author=self.admin) for i in range(1)]
        self.session.add_all(self.articles)
        self.session.commit()

    def test_api(self):
        rsp = self.client.get('/api/')
        self.assertEqual(rsp.status_code, 200)
        self.assertEqual(rsp.get_data(True), 'Test.')

    def test_GET_Resource(self):
        rsp = self.client.get('/api/articles/1')
        self.assertEqual(rsp.status_code, 200)
        self.assertEqual(rsp.get_data(True), '{"id": 1, "title": "article:0", "content": "test article:0", "author_id": 1}')

    def test_GET_Resource_404(self):
        rsp = self.client.get('/api/articles/10')
        self.assertEqual(rsp.status_code, 404)
        self.assertEqual(rsp.get_data(True), '{"code": 404, "message": "The requested URL was not found on the server.  If you entered the URL manually please check your spelling and try again."}')

    def test_PUT_Resource(self):
        rsp = self.client.put('/api/articles/1', json={'title': 'edited title', 'content': 'edited content', 'author_id':1})
        self.assertEqual(rsp.status_code, 201)
        self.assertEqual(rsp.get_json(), {'id': 1, 'title': 'edited title', 'content': 'edited content', 'author_id': 1})
        edited = Article.query.filter_by(id=1).one()
        self.assertEqual(edited.pre_serialize(), {'id': 1, 'title': 'edited title', 'content': 'edited content', 'author_id': 1})

    '''def test_POST_ResourceList(self):
        rsp = self.client.post('/api/articles', json={'title': 'new article', 'content': 'some content', 'author_id':1})
        edited = Article.query.filter_by(id=1).one()
        self.assertEqual(rsp.status_code, 200)
        self.assertEqual(rsp.get_json(), edited.pre_serialize())'''

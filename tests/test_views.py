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
        self.articles = [Article(title='article:%d'%i, content='test article:%d'%i, author=self.admin) for i in range(100)]
        self.session.add_all(self.articles)
        self.session.commit()

    def test_api(self):
        rsp = self.client.get('/api/')
        self.assertEqual(rsp.status_code, 200)
        self.assertEqual(rsp.get_data(True), 'Test.')

    def test_GET_Resource(self):
        rsp = self.client.get('/api/articles/1')
        self.assertEqual(rsp.status_code, 200)
        self.assertEqual(rsp.get_json(), {"id": 1, "title": "article:0", "content": "test article:0", "author_id": 1})

    def test_GET_Resource_List(self):
        rsp = self.client.get('/api/articles')
        self.assertEqual(rsp.status_code, 200)
        rsp_data = rsp.get_json()
        self.assertEqual(rsp_data['paging'], {'total': 100, 'next': False})

        rsp = self.client.get('/api/articles?limit=20&offset=20')
        self.assertEqual(rsp.status_code, 200)
        rsp_data = rsp.get_json()
        self.assertEqual(rsp_data['paging'], {'total': 100, 'next': True})

        rsp = self.client.get('/api/articles?limit=20&offset=asd')
        self.assertEqual(rsp.status_code, 400)
        rsp_data = rsp.get_json()
        self.assertEqual(rsp_data, {'code': 400, 'message': 'Offset or limit must an integer'})
        
        rsp = self.client.get('/api/articles?limit=20&offset=200')
        self.assertEqual(rsp.status_code, 200)
        rsp_data = rsp.get_json()
        self.assertEqual(rsp_data, {'paging': {'total': 100, 'next': False}, 'data': []})


    def test_GET_DELETE_404(self):
        error = {'code': 404, 'message': 'Resource not found'}
        rsp = self.client.get('/api/articles/101')
        self.assertEqual(rsp.status_code, 404)
        self.assertEqual(rsp.get_json(), error)
        rsp = self.client.delete('/api/articles/101')
        self.assertEqual(rsp.status_code, 404)
        self.assertEqual(rsp.get_json(), error)


    def test_POST_PUT_400(self):
        invalid_data = {'invalid':'this is a invalid field','title': 'edited title', 'content': 'edited content', 'author_id':1}
        # PUT
        before_put = Article.query.filter_by(id=1).one()
        rsp = self.client.put('/api/articles/1', json=invalid_data)
        self.assertEqual(rsp.status_code, 400)
        self.assertEqual(rsp.get_json(), {'code': 400, 'message': {'errors': {'invalid': ["TypeError: 'invalid' is not a field of Article"]}, 'invalid data': {'author_id': 1,'content': 'edited content','invalid': 'this is a invalid field','title': 'edited title'}}})
        after_put = Article.query.filter_by(id=1).one()
        self.assertEqual(before_put.pre_serialize(), after_put.pre_serialize())
        # POST
        rsp = self.client.post('/api/articles', json=invalid_data)
        self.assertEqual(rsp.status_code, 400)
        self.assertEqual(rsp.get_json(), {'code': 400, 'message': {'errors': {'invalid': ["TypeError: 'invalid' is not a field of Article"]}, 'invalid data': {'author_id': 1,'content': 'edited content','invalid': 'this is a invalid field','title': 'edited title'}}})

    def test_POST_PUT_DELETE_Resource(self):
        # POST
        data = {'title': 'new article', 'content': 'some content', 'author_id':1}
        rsp = self.client.post('/api/articles', json=data)
        self.assertEqual(rsp.status_code, 201)
        rsp_data = rsp.get_json()
        self.assertTrue('id' in rsp_data)
        aid = rsp_data['id']
        # PUT
        data.update({'title': 'edited title', 'content': 'edited content', 'author_id':1})
        rsp = self.client.put('/api/articles/%s'%aid, json=data)
        self.assertEqual(rsp.status_code, 201)
        data.update({'id':aid})
        self.assertEqual(rsp.get_json(), data)
        edited = Article.query.filter_by(id=aid).one()
        self.assertEqual(edited.pre_serialize(), data)
        # DELETE
        rsp = self.client.delete('/api/articles/%s'%aid)
        self.assertEqual(rsp.status_code, 204)
        self.assertEqual(rsp.get_data(), b'')
        q = self.session.query(Article.query.filter_by(id=aid).exists()).scalar()
        self.assertEqual(q, False)
        


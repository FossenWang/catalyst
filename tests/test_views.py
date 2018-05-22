from flask_fossen.testcases import FlaskTestCase

from .test_app.app import create_app, db
from .test_app.app.database import User, Article


class ViewTest(FlaskTestCase):
    app = create_app()
    db = db

    def setUp(self):
        self.session = self.db.session
        self.admin = User(username='admin', email='admin@test.com', password='asd123')
        self.session.add(self.admin)
        self.session.commit()
        self.articles = [Article(title='article:%d'%i, content='test article:%d'%i, author=self.admin) for i in range(100)]
        self.session.add_all(self.articles)
        self.session.commit()

    def test_api(self):
        rsp = self.client.get('/api/')
        self.assertEqual(rsp.status_code, 200)
        self.assertEqual(rsp.get_data(True), 'Test.')

        # test_GET_Resource
        rsp = self.client.get('/api/articles/1')
        self.assertEqual(rsp.status_code, 200)
        self.assertEqual(rsp.get_json(), {"id": 1, "title": "article:0", "content": "test article:0", "author_id": 1})

        # test GET Resource List
        rsp = self.client.get('/api/articles')
        self.assertEqual(rsp.status_code, 200)
        rsp_data = rsp.get_json()
        self.assertEqual(rsp_data['paging'], {'total': 100, 'limit': -1, 'offset': 0, 'next': False})

        rsp = self.client.get('/api/articles?limit=20&offset=20')
        self.assertEqual(rsp.status_code, 200)
        rsp_data = rsp.get_json()
        self.assertEqual(rsp_data['paging'], {'total': 100, 'limit': 20, 'offset': 20, 'next': True})

        rsp = self.client.get('/api/articles?limit=20&offset=200')
        self.assertEqual(rsp.status_code, 200)
        rsp_data = rsp.get_json()
        self.assertEqual(rsp_data, {'paging': {'total': 100, 'limit': 20, 'offset': 200, 'next': False}, 'data': []})

        rsp = self.client.get('/api/articles?limit=20&offset=100')
        self.assertEqual(rsp.status_code, 200)
        rsp_data = rsp.get_json()
        self.assertEqual(rsp_data, {'paging': {'total': 100, 'limit': 20, 'offset': 100, 'next': False}, 'data': []})

        rsp = self.client.get('/api/articles?limit=20&offset=asd')
        self.assertEqual(rsp.status_code, 400)
        rsp_data = rsp.get_json()
        self.assertEqual(rsp_data, 'Offset or limit must an integer')


        # test GET and DELETE 404
        error = 'Resource not found'
        rsp = self.client.get('/api/articles/101')
        self.assertEqual(rsp.status_code, 404)
        self.assertEqual(rsp.get_json(), error)
        rsp = self.client.delete('/api/articles/101')
        self.assertEqual(rsp.status_code, 404)
        self.assertEqual(rsp.get_json(), error)


        # test POST and PUT 400
        invalid_data = {'title': None, 'content': 'edited content', 'author_id':1}
        # PUT
        before_put = Article.query.filter_by(id=1).one()
        rsp = self.client.put('/api/articles/1', json=invalid_data)
        self.assertEqual(rsp.status_code, 400)
        self.assertEqual(rsp.get_json()['errors'], {'title': ['ValueError: Ensure value is not None']})
        after_put = Article.query.filter_by(id=1).one()
        self.assertEqual(before_put.serialize(), after_put.serialize())
        # POST
        rsp = self.client.post('/api/articles', json=invalid_data)
        self.assertEqual(rsp.status_code, 400)
        self.assertEqual(rsp.get_json()['errors'], {'title': ['ValueError: Ensure value is not None']})

        # test POST & PUT & DELETE_Resource
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
        self.assertEqual(edited.serialize(), data)
        # DELETE
        rsp = self.client.delete('/api/articles/%s'%aid)
        self.assertEqual(rsp.status_code, 204)
        self.assertEqual(rsp.get_data(), b'')
        q = self.session.query(Article.query.filter_by(id=aid).exists()).scalar()
        self.assertEqual(q, False)
        


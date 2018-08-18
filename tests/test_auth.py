from flask_fossen.testcases import FlaskTestCase
from flask_fossen.auth import PasswordMixin

from .test_app.app import create_app, db
from .test_app.app.database import User, Article


class AuthTest(FlaskTestCase):
    app = create_app()
    db = db

    def setUp(self):
        self.session = self.db.session()
        self.admin = User(username='admin',
                          email='admin@test.com', password='asd123')
        self.session.add(self.admin)
        self.session.commit()
        self.articles = [Article(title='article:%d' % i, content='test article:%d' %
                                 i, author=self.admin) for i in range(100)]
        self.session.add_all(self.articles)
        self.session.commit()

    def test_views(self):
        # test passwordmixin
        raw = 'asd123'
        psw = PasswordMixin()
        psw.password = raw
        self.assertTrue(psw.check_password(raw))
        # login required
        rsp = self.client.get('/api/user')
        self.assertEqual(rsp.status_code, 401)
        self.assertEqual(rsp.get_json(), {'msg': 'Missing cookie "access_token_cookie"'})
        # register a new user
        data = {'password': 'asd123', 'username': 666, 'email': '666@666.com'}
        user_info = {'id': 2, 'username': '666', 'email': '666@666.com'}
        rsp = self.client.post('/api/user', json=data)
        self.assertEqual(rsp.status_code, 201)
        self.assertEqual(rsp.get_json(), user_info)
        # login fail
        rsp = self.client.post('/api/login', json={})
        self.assertEqual(rsp.status_code, 401)
        self.assertEqual(rsp.get_json(), {'login': False})
        # login
        rsp = self.client.post('/api/login', json=data)
        self.assertEqual(rsp.status_code, 200)
        self.assertEqual(rsp.get_json(), {'login': True})
        access_cookie = rsp.headers['Set-Cookie']
        # get user info
        rsp = self.client.get('/api/user')
        self.assertEqual(rsp.status_code, 200)
        self.assertEqual(rsp.get_json(), user_info)
        # refresh
        rsp = self.client.post('/api/token/refresh')
        self.assertEqual(rsp.status_code, 200)
        self.assertEqual(rsp.get_json(), {'refresh': True})
        refresh_cookie = rsp.headers['Set-Cookie']
        self.assertNotEqual(access_cookie, refresh_cookie)
        # logout
        rsp = self.client.post('/api/logout')
        self.assertEqual(rsp.status_code, 200)
        self.assertEqual(rsp.get_json(), {'logout': True})
        self.assertEqual(
            rsp.headers['Set-Cookie'], 'access_token_cookie=; Expires=Thu, 01-Jan-1970 00:00:00 GMT; HttpOnly; Path=/')

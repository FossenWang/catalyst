from flask_fossen.testcases import FlaskTestCase
from flask_fossen.http import JSONResponse, json

from .test_app.app import create_app, db
from .test_app.app.database import User, Article

class HttpTest(FlaskTestCase):
    def test_json_response(self):
        msg = {'code':1, 'msg':'success!', 'data':'nothing'}
        jr = JSONResponse(msg)
        self.assertEqual(jr.status_code, 200)
        self.assertEqual(jr.get_data(), bytes(json.dumps(msg), 'utf-8'))
        self.assertEqual(jr.headers['content-type'], 'application/json')

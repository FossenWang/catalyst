from flask_fossen.testcases import FlaskTestCase
from flask_fossen.http import JSONResponse, json, handle_http_exception
from werkzeug.exceptions import HTTPException, abort

class HttpTest(FlaskTestCase):
    def test_json_response(self):
        msg = {'code':1, 'msg':'success!', 'data':'nothing'}
        jr = JSONResponse(msg)
        self.assertEqual(jr.status_code, 200)
        self.assertEqual(jr.get_data(), bytes(json.dumps(msg), 'utf-8'))
        self.assertEqual(jr.headers['content-type'], 'application/json')
    
    def test_error_handle(self):
        rsp = self.raise_error_and_get_response(400)
        self.assertEqual(rsp.status_code, 400)
        self.assertEqual(rsp.get_data(True), '"The browser (or proxy) sent a request that this server could not understand."')

        rsp = self.raise_error_and_get_response(400, {'errors':['some errors happens']})
        self.assertEqual(rsp.status_code, 400)
        self.assertEqual(rsp.get_data(True), '{"errors": ["some errors happens"]}')

    def raise_error_and_get_response(self, status, description=None):
        try:
            abort(status, description)
        except HTTPException as e:
            return handle_http_exception(e)

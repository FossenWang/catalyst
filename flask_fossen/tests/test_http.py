from werkzeug.exceptions import HTTPException, abort

from flask_fossen.http import JSONResponse, handle_http_exception, json
from flask_fossen.testcases import FlaskTestCase


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

        rsp = handle_http_exception(TypeError)
        self.assertEqual(rsp.get_data(True), '{"msg": "The server encountered an internal error and was unable to complete your request.  Either the server is overloaded or there is an error in the application."}')

    def raise_error_and_get_response(self, status, description=None):
        try:
            abort(status, description)
        except HTTPException as e:
            return handle_http_exception(e)

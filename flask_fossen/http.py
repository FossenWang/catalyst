import json
from werkzeug.wrappers import Response
from werkzeug.exceptions import HTTPException, default_exceptions

class JSONResponse(Response):
    """
    Return a JSON Response
    :param response: an object that can be serialized as JSON by json.dumps()
    :param status: a string with a status or an integer with the status code
    """
    def __init__(self, response=None, is_json=False, status=None, content_type='application/json', **kwargs):
        if not is_json:
            response=json.dumps(response)
        super().__init__(response=response, status=status, content_type=content_type, **kwargs)


class JSONResponseBadRequest(JSONResponse):
    default_status = 400


def handle_http_exception(e):
    if e.description and e.code in default_exceptions:
        description = e.description
    else:
        description = default_exceptions[e.code].description
    return JSONResponse({'code': e.code, 'message': description}, status=e.code)


def register_json_error_handle(app):
    app.register_error_handler(HTTPException, handle_http_exception)

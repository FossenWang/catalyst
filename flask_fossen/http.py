import json
from werkzeug.wrappers import Response
from werkzeug.exceptions import HTTPException, default_exceptions
from werkzeug.routing import RequestRedirect


class JSONResponse(Response):
    """
    Return a JSON Response
    :param response: an object that can be serialized as JSON by json.dumps()
    :param status: a string with a status or an integer with the status code
    """

    def __init__(self, response=None, is_json=False, status=None,
                 content_type='application/json', **kwargs):

        if not is_json:
            response = json.dumps(response)

        super().__init__(response=response, status=status,
                         content_type=content_type, **kwargs)


def handle_http_exception(e):
    if isinstance(e, HTTPException):
        description = ''
        if e.description:
            description = e.description
        elif e.code in default_exceptions:
            description = {'msg': default_exceptions[e.code].description}
        elif isinstance(e, RequestRedirect):
            return e
        else:
            description = str(e)
        return JSONResponse(description, status=e.code)
    else:
        return JSONResponse(
            {'msg': default_exceptions[500].description},
            status=500)


def register_json_error_handle(app):
    app.register_error_handler(HTTPException, handle_http_exception)

import json
from werkzeug.wrappers import Response


class JSONResponse(Response):
    """
    Return a JSON Response
    :param response: an object that can be serialized as JSON by json.dumps()
    :param status: a string with a status or an integer with the status code
    """
    def __init__(self, response=None, status=None, content_type='application/json', **kwargs):
        response=json.dumps(response)
        super().__init__(response=response, status=status, content_type=content_type, **kwargs)


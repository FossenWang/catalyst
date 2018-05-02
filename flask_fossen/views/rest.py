
from flask_fossen.http import JSONResponse
from flask_fossen.models import Serializable
from .base import SingleObjectMixin, CreateMixin, MethodView, BaseView


class JSONResponseMixin:
    """Return JSON response"""
    def make_response(self, context, **response_kwargs):
        return JSONResponse(context, **response_kwargs)


class BaseSingleResource(SingleObjectMixin, CreateMixin, BaseView):
    """Restful base single resource view"""

    # PUT is a valid HTTP verb for creating (with a known URL) or editing an
    # object, note that some browsers only support POST for now.
    def put(self, *args, **kwargs):
        return self.post(*args, **kwargs)


class SingleResource(JSONResponseMixin, BaseSingleResource):

    def get_context_data(self, **kwargs):
        """Convert object to serializable python data structure"""
        return self.object.pre_serialize()

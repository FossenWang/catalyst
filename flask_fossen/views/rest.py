
from flask_fossen.http import JSONResponse
from flask_fossen.models import Serializable
from .base import SingleObjectMixin, CreateMixin, MethodView, BaseView, UpdateMixin


class JSONResponseMixin:
    """Return JSON response"""
    def make_response(self, context, **response_kwargs):
        return JSONResponse(context, **response_kwargs)


class BaseResource(SingleObjectMixin, UpdateMixin, BaseView):
    """Restful base single resource view"""



class Resource(JSONResponseMixin, BaseResource):

    def get_context_data(self, **kwargs):
        """Convert object to serializable python data structure"""
        return self.object.pre_serialize()


from flask_fossen.http import JSONResponse
from flask_fossen.models import Serializable
from .base import SingleObjectMixin, CreateMixin, BaseView, UpdateMixin, DeleteMixin, MultipleObjectMixin


class JSONResponseMixin:
    """Return JSON response"""
    def make_response(self, context, **response_kwargs):
        return JSONResponse(context, **response_kwargs)


class BaseResource(SingleObjectMixin, UpdateMixin, DeleteMixin, BaseView):
    """Base single resource view"""


class Resource(JSONResponseMixin, BaseResource):
    """
    Restful single resource view which can
    show, edit and delete a single resource.
    """


class BaseResourceList(MultipleObjectMixin, CreateMixin, BaseView):
    """Base resource list view"""


class ResourceList(JSONResponseMixin, BaseResourceList):
    """
    Restful resource list view which can show a
    list of resources and create a new resource.
    """


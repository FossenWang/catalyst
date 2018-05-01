
from flask_fossen.http import JSONResponse
from flask_fossen.models import Serializable
from .base import SingleObjectMixin, BaseView


class JSONResponseMixin:
    """Return JSON response"""
    def make_response(self, context, **response_kwargs):
        return JSONResponse(context, **response_kwargs)


class BaseSingleResource(SingleObjectMixin, BaseView):
    """Restful base single resource view"""

    def get(self, *args, **kwargs):
        return self.make_response(self.get_object())

    def post(self, *args, **kwargs):
        form = self.get_form()
        if form.validate():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    # PUT is a valid HTTP verb for creating (with a known URL) or editing an
    # object, note that some browsers only support POST for now.
    def put(self, *args, **kwargs):
        return self.post(*args, **kwargs)


class SingleResource(JSONResponseMixin, BaseSingleResource):

    def get_object(self, **kwargs):
        """Convert object to serializable python data structure"""
        obj = super().get_object()
        if isinstance(obj, Serializable):
            obj = obj.pre_serialize()
        return obj

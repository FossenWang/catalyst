from flask import request, abort
from flask.views import View, MethodView
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.query import Query

from .http import JSONResponse
from .models import Serializable


class BaseView(MethodView):
    def dispatch_request(self, *args, **kwargs):
        # add attributes
        self.args = args
        self.kwargs = kwargs
        return super().dispatch_request()


class ContextMixin:
    """
    A default context mixin that passes the keyword arguments received by
    get_context_data() as context data.
    """
    extra_context = None

    def get_context_data(self, **kwargs):
        if self.extra_context is not None:
            kwargs.update(self.extra_context)
        return kwargs


class SingleObjectMixin(ContextMixin):
    """
    Provide the ability to retrieve a single object for further manipulation.
    """
    model = None
    query = None
    id_url_kwarg = 'id'
    serializing = True

    def get(self, *args, **kwargs):
        self.object = self.get_object()
        return self.make_response(self.get_context_data())

    def get_query(self):
        """
        Return the `query` that will be used to look up the object.

        This method is called by the default implementation of get_object() and
        may not be called if get_object() is overridden.
        """
        if self.query is None:
            if self.model is not None:
                return self.model.query
            else:
                raise TypeError(
                    "%(cls)s is missing a query. Define "
                    "%(cls)s.model, %(cls)s.query, or override "
                    "%(cls)s.get_query()." % {
                        'cls': self.__class__.__name__
                    }
                )
        assert isinstance(self.query, Query), \
        "'query' Must be an instance of 'sqlalchemy.orm.query.Query'"
        return self.query

    def get_object(self, query=None):
        """
        Return the object the view is displaying.

        Require `self.query` and a `id` argument in the URLconf.
        Subclasses can override this to return any object.
        """
        # Use a custom query if provided; this is required for subclasses
        if query is None:
            query = self.get_query()

        # Next, try looking up by primary key.
        obj_id = self.kwargs.get(self.id_url_kwarg)
        if obj_id is not None:
            query = query.filter(self.model.id==obj_id)
        else:
            raise AttributeError("No object id")
        
        try:
            # Get the single item from the filtered query
            obj = query.one()
        except NoResultFound:
            raise abort(404, 'Resource not found')
        return obj

    def serialize_object(self, obj, related=[], ignore=[]):
        return obj.serialize(related=related, ignore=ignore)

    def get_context_data(self, **context):
        """Insert the single object into the context dict."""
        if self.object:
            if self.serializing:
                context.update(self.serialize_object(self.object))
            else:
                context['object'] = self.object
        return super().get_context_data(**context)


class MultipleObjectMixin(ContextMixin):
    """A mixin for views manipulating multiple objects."""
    model = None
    query = None
    limit = None
    offset = None
    ordering = None
    serializing = True

    def get(self, *args, **kwargs):
        self.object_list = self.get_object_list()
        return self.make_response(self.get_context_data())

    def get_query(self):
        """
        Return the list of items for this view.
        Must be an instance of 'Query'.
        """
        if self.query is None:
            if self.model is not None:
                query = self.model.query
                if self.ordering:
                    query = query.order_by(self.ordering)
            else:
                raise TypeError(
                    "%(cls)s is missing a query. Define "
                    "%(cls)s.model, %(cls)s.query, or override "
                    "%(cls)s.get_query()." % {
                        'cls': self.__class__.__name__
                    }
                )
        assert isinstance(query, Query), \
        "'query' Must be an instance of 'sqlalchemy.orm.query.Query'"
        return query

    def paginate_query(self, query):
        """
        paginate query by offset and limit,
        override this method to provide other pagination method
        """
        total = self.get_total()
        limit = self.get_limit()
        offset = self.get_offset()

        query = query.limit(limit).offset(offset)

        if offset >= total or limit == 0:
            # Reduce unnecessary database access.
            query.all = lambda:[]
        
        self.paging = {'total': total, 'limit':limit, 'offset':offset, 'next': total > (limit + offset) and limit >= 0}
        return query

    def get_limit(self):
        limit = request.args.get('limit', self.limit)
        try:
            if limit is None:
                limit = -1
            else:
                limit = int(limit)
        except ValueError:
            raise abort(400, "Offset or limit must an integer")
        return limit

    def get_offset(self):
        offset = request.args.get('offset', self.offset)
        try:
            if offset is None:
                offset = 0
            else:
                offset = int(offset)
        except ValueError:
            raise abort(400, "Offset or limit must an integer")
        return offset

    def get_total(self):
        return self.get_query().count()

    def get_object_list(self):
        object_list = self.paginate_query(self.get_query()).all()
        return object_list

    def serialize_object_list(self, object_list, related=[], ignore=[]):
        return self.model.serialize(object_list, related=related, ignore=ignore)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.paging is not None:
            context['paging'] = self.paging
        if self.object_list is not None:
            if self.serializing:
                object_list = self.serialize_object_list(self.object_list)
            else:
                object_list = self.object_list
            context['data'] = object_list
        return context


class ValidatorMixin:
    def get_data(self):
        return request.get_json()

    def validate_data(self, data):
        return self.model.validate_data(data)

    def data_valid(self, data, extra={}):
        self.object = self.save_object(data)
        context = self.object.serialize()
        context.update(extra)
        return self.make_response(context, status=201)

    def data_invalid(self, data, errors, **kwargs):
        raise abort(400, {'invalid data': data, 'errors': errors})


class UpdateMixin(ValidatorMixin):
    """Update a single object."""
    db = None

    def put(self, *args, **kwargs):
        self.data = self.get_data()
        is_valid, errors = self.validate_data(self.data)
        if is_valid:
            return self.data_valid(self.data)
        else:
            return self.data_invalid(self.data, errors)

    def save_object(self, data):
        obj = self.get_object()
        self.db.session.add(obj)
        self.model.update(obj, data)
        self.db.session.commit()
        return obj


class CreateMixin(ValidatorMixin):
    """Create a single object."""
    db = None

    def post(self, *args, **kwargs):
        self.data = self.get_data()
        is_valid, errors = self.validate_data(self.data)
        if is_valid:
            return self.data_valid(self.data)
        else:
            return self.data_invalid(self.data, errors)

    def save_object(self, data):
        obj = self.model.create(data)
        self.db.session.add(obj)
        self.db.session.commit()
        return obj


class DeleteMixin:
    """Delete a single object."""
    db = None
    def delete(self, *args, **kwargs):
        obj = self.get_object()
        self.db.session.delete(obj)
        self.db.session.commit()
        return self.make_response('', status=204)


class JSONResponseMixin:
    """Return JSON response"""
    def make_response(self, context, **response_kwargs):
        """
        Return a JSON Response
        :param response: an object that can be serialized as JSON by json.dumps()
        :param status: a string with a status or an integer with the status code
        """
        return JSONResponse(context, **response_kwargs)


class JSONView(JSONResponseMixin, BaseView):
    """Returns JSON data"""


class Resource(SingleObjectMixin, UpdateMixin, DeleteMixin, JSONView):
    """
    Restful single resource view which can
    show, edit and delete a single resource.
    """


class ResourceList(MultipleObjectMixin, CreateMixin, JSONView):
    """
    Restful resource list view which can show a
    list of resources and create a new resource.
    """


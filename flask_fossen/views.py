from flask import request, abort
from flask.views import MethodView
from sqlalchemy.orm.query import Query
from sqlalchemy.exc import DBAPIError

from .http import JSONResponse
from .models import SerializableModel


class BaseView(MethodView):
    def dispatch_request(self, *args, **kwargs):
        # add attributes
        self.args = args
        self.kwargs = kwargs
        return super().dispatch_request(*args, **kwargs)


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
        return self.make_response(self.get_context_data())

    def get_query(self):
        """
        Return the `query` that will be used to look up the object.
        This method is called by the default implementation of get_object() and
        may not be called if get_object() is overridden.
        """
        if self.query is None:
            if self.db is not None and self.model is not None:
                return self.db.session.query(self.model)
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

    def filter_query(self, query):
        """Filter by id, override this method to change filter condition"""
        obj_id = self.kwargs.get(self.id_url_kwarg) \
            or request.args.get(self.id_url_kwarg)
        if obj_id is None:
            abort(400, {'msg': "No object id"})
        else:
            query = query.filter(self.model.id == obj_id)
        return query

    def get_object(self):
        """
        Return the object the view is displaying.
        Require `self.query` and a `id` argument in the URLconf.
        Subclasses can override this to return any object.
        """
        query = self.get_query()
        query = self.filter_query(query)
        obj = query.one_or_none()
        if obj is None:
            abort(404, {'msg': 'Resource not found'})
        return obj

    def serialize_object(self, obj, related=[], ignore=[]):
        return obj.serialize(related=related, ignore=ignore)

    def get_context_data(self, **context):
        """Insert the single object into the context dict."""
        self.object = self.get_object()
        if self.object:
            if self.serializing:
                context.update(self.serialize_object(self.object))
            else:
                context['object'] = self.object
        return super().get_context_data(**context)


class BaseMultipleObjectMixin(ContextMixin):
    """
    Provide the ability to retrieve mutiple objects for further manipulation.
    """
    model = None
    query = None
    limit = None
    offset = None
    ordering = None
    serializing = True
    paging_data = None
    paging = True

    def get(self, *args, **kwargs):
        return self.make_response(self.get_context_data())

    def get_query(self):
        """
        Return the list of items for this view.
        Must be an instance of 'Query'.
        """
        if self.query is None:
            if self.db is not None and self.model is not None:
                query = self.db.session.query(self.model)
                if self.ordering is not None:
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
        """Override this method to provide pagination method"""
        return query

    def get_object_list(self):
        query = self.get_query()
        if self.paging:
            query = self.paginate_query(query)
        object_list = query.all()
        return object_list

    def serialize_object_list(self, object_list, related=[], ignore=[]):
        return self.model.serialize(object_list, related=related, ignore=ignore)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.object_list = self.get_object_list()
        if self.object_list is not None:
            if self.serializing:
                object_list = self.serialize_object_list(self.object_list)
            else:
                object_list = self.object_list
            context['data'] = object_list
        if self.paging_data is not None:
            context['paging'] = self.paging_data
        return context


class LimitOffsetMixin:
    """Paginate query by offset and limit"""
    limit = None
    offset = None

    def paginate_query(self, query):
        """
        Paginate query by offset and limit
        """
        total = self.get_total()
        limit = self.get_limit()
        offset = self.get_offset()

        if limit:
            query = query.limit(limit)

        if offset:
            query = query.offset(offset)

        if offset >= total or limit == 0:
            # Reduce unnecessary database access.
            query.all = lambda: []

        self.paging_data = {
            'total': total, 'limit': limit, 'offset': offset,
            'next': bool(limit) and total > (limit + offset)
        }
        return query

    def get_limit(self):
        limit = request.args.get('limit', self.limit)
        try:
            if limit:
                limit = int(limit)
                if limit < 0:
                    raise ValueError
        except ValueError:
            abort(400, {'msg': "Limit must be an Positive integer or 0"})
        return limit

    def get_offset(self):
        offset = request.args.get('offset', self.offset)
        try:
            if offset is None:
                offset = 0
            else:
                offset = int(offset)
                if offset < 0:
                    raise ValueError
        except ValueError:
            abort(400, {'msg': "Offset must be an Positive integer or 0"})
        return offset

    def get_total(self):
        return self.get_query().count()


class PaginationMixin:
    """To be implemented"""


class MultipleObjectMixin(LimitOffsetMixin, BaseMultipleObjectMixin):
    """
    Provide the ability to retrieve mutiple objects for further manipulation.
    """


class ValidationMixin:
    """Validate request data"""
    validator_set = None

    def get_data(self):
        if request.is_json:
            return request.get_json()
        else:
            abort(406, {'msg': 'Only accept JSON data'})

    def get_validator_set(self):
        if self.validator_set:
            return self.validator_set
        else:
            assert issubclass(self.model, SerializableModel), \
                'Need validator_set or SerializableModel'
            return self.model

    def validate_data(self, data):
        return self.get_validator_set().validate_data(data)

    def data_valid(self, data):
        try:
            self.object = self.save_object(data)
        except DBAPIError:
            abort(400, {'msg': 'Database operation fails'})
        return self.make_response(self.get_success_data(data), status=201)

    def get_success_data(self, data):
        if self.object:
            return self.object.serialize()
        else:
            return data

    def data_invalid(self, data, errors, **kwargs):
        abort(400, {
            'msg': 'Invalid data',
            'invalid data': data, 'errors': errors
        })


class UpdateMixin(ValidationMixin):
    """Update a single object."""
    db = None

    def put(self, *args, **kwargs):
        self.data = self.get_data()
        result = self.validate_data(self.data)
        if result.is_valid:
            return self.data_valid(result.valid_data)
        else:
            return self.data_invalid(result.invalid_data, result.errors)

    def save_object(self, data):
        obj = self.get_object()
        self.model.update(obj, data)
        self.db.session.commit()
        return obj


class CreateMixin(ValidationMixin):
    """Create a single object."""
    db = None

    def post(self, *args, **kwargs):
        self.data = self.get_data()
        result = self.validate_data(self.data)
        if result.is_valid:
            return self.data_valid(result.valid_data)
        else:
            return self.data_invalid(result.invalid_data, result.errors)

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

    def make_response(self, context, status=None, is_json=False, **kwargs):
        """
        Return a JSON Response
        :param response: an object that can be serialized as JSON by json.dumps()
        :param status: a string with a status or an integer with the status code
        """
        return JSONResponse(context, status=status, is_json=is_json, **kwargs)


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

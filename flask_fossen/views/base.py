from flask import request, abort
from flask.views import View, MethodView
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.query import Query


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

    def get_context_data(self, **context):
        """Insert the single object into the context dict."""
        if self.object:
            context.update(self.object.pre_serialize())
        return super().get_context_data(**context)


class MultipleObjectMixin(ContextMixin):
    """A mixin for views manipulating multiple objects."""
    model = None
    query = None
    limit = None
    offset = None
    ordering = None
    _total = None

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

        if self.ordering:
            query = query.order_by(self.ordering)

        return query


    def paginate_query(self, query):
        """
        paginate query by offset and limit,
        override this method to provide other pagination method
        """
        offset = request.args.get('offset', self.offset)
        query = query.offset(offset)

        limit = request.args.get('limit', self.limit)
        query = query.limit(limit)

        total = self.get_total()
        if limit is None: limit = -1
        if offset is None: offset = 0
        try:
            self.paging = {'total': total, 'next': False if int(limit)<0 else total > (int(limit) + int(offset))}
        except ValueError:
            raise abort(400, "Offset or limit must an integer")

        if int(offset) > total or limit == 0:
            # 减少不必要的数据库访问
            query.all = lambda:[]
        return query

    def get_total(self):
        cls = self.__class__
        if cls._total is None:
            cls._total = self.get_query().count()
        return cls._total

    def get_object_list(self):
        return self.paginate_query(self.get_query()).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.paging is not None:
            context['paging'] = self.paging
        if self.object_list is not None:
            context['data'] = self.model.pre_serialize(self.object_list)
        return context



class ValidatorMixin:
    def get_validator(self):
        '''Get the validator, which is ValidationModel by default.
        Override this method to get another validator.'''
        return self.model

    def data_valid(self, data, extra={}):
        obj = self.save_object(data)
        context = obj.pre_serialize()
        context.update(extra)
        return self.make_response(context, status=201)

    def data_invalid(self, data, errors, **kwargs):
        raise abort(400, {'invalid data': data, 'errors': errors})


class UpdateMixin(ValidatorMixin):
    """Update a single object."""
    db = None

    def put(self, *args, **kwargs):
        self.validator = self.get_validator()
        self.data = request.get_json()
        is_valid, errors = self.validator.validate_data(self.data)
        if is_valid:
            return self.data_valid(self.data)
        else:
            return self.data_invalid(self.data, errors)

    def save_object(self, data):
        obj = self.get_object()
        self.db.session.add(obj)
        self.validator.update(obj, data)
        self.db.session.commit()
        return obj


class CreateMixin(ValidatorMixin):
    """Create a single object."""
    db = None

    def post(self, *args, **kwargs):
        self.validator = self.get_validator()
        self.data = request.get_json()
        is_valid, errors = self.validator.validate_data(self.data)
        if is_valid:
            return self.data_valid(self.data)
        else:
            return self.data_invalid(self.data, errors)

    def save_object(self, data):
        obj = self.validator.create(data)
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


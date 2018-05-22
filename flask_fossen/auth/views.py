from flask import request, abort
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, \
jwt_refresh_token_required, create_refresh_token, get_jwt_identity, \
set_access_cookies, set_refresh_cookies, unset_jwt_cookies, decode_token, get_jwt_identity

from ..views import JSONView, CreateMixin, SingleObjectMixin


def set_jwt_cookies(response, identity):
    """Set access and refresh token in cookies"""
    access_token = create_access_token(identity=identity)
    refresh_token = create_refresh_token(identity=identity)
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return (access_token, refresh_token)


class BaseUserView(SingleObjectMixin, CreateMixin, JSONView):
    """Register user and show user infomartion"""
    identity_attribute = 'username'

    @jwt_required
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    def filter_query(self, query):
        identity = get_jwt_identity()
        user_identity = getattr(self.model, self.identity_attribute)
        return query.filter(user_identity==identity)

    def get_object(self):
        query = self.get_query()
        query = self.filter_query(query)
        user = query.one_or_none()
        if user is None:
            raise abort(401)
        return user


class BaseLoginView(JSONView):
    """
    Log in the user by setting access and refresh tokens in cookies,
    which contain user's identity
    """
    model = None
    identity_attribute = 'username'

    def post(self):
        self.user = self.authenticate()
        if self.user:
            return self.login()
        else:
            return self.login_failed()

    def authenticate(self):
        data = request.get_json()
        identity = data.get(self.identity_attribute, None)
        password = data.get('password', None)
        user_identity = getattr(self.model, self.identity_attribute)
        user = self.model.query.filter(user_identity==identity).one_or_none()
        if user.check_password(password):
            return user

    def login(self):
            rsp = self.make_response({'login': True})
            set_jwt_cookies(rsp, getattr(self.user, self.identity_attribute))
            return rsp

    def login_failed(self):
        return self.make_response({'login': False}, status=401)


class RefreshToken(JSONView):
    """Refresh the access token"""
    @jwt_refresh_token_required
    def post(self):
        user_identity = get_jwt_identity()
        access_token = create_access_token(identity=user_identity)
        rsp = self.make_response({'refresh': True})
        set_access_cookies(rsp, access_token)
        return rsp


class LogoutView(JSONView):
    """Log out the user by setting empty token cookie"""
    def post(self):
        rsp = self.make_response({'logout': True})
        unset_jwt_cookies(rsp)
        return rsp


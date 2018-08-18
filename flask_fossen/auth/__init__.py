import datetime
from .models import AbstractUser, PasswordMixin
from .views import BaseLoginView, LogoutView, \
RefreshToken, BaseUserView, LoginRequiredMixin, \
set_jwt_cookies


class AuthConfig:
    # JWT Configuration
    JWT_SECRET_KEY = 'change_this'
    JWT_TOKEN_LOCATION = ['cookies']
    JWT_ACCESS_COOKIE_PATH = '/'
    # Should set refresh path to a certain url, like '/token/refresh'
    JWT_REFRESH_COOKIE_PATH = '/'
    JWT_COOKIE_CSRF_PROTECT = False
    JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = datetime.timedelta(days=30)


__all__ = [
    'AbstractUser', 'PasswordMixin', 'BaseLoginView', \
    'LogoutView', 'RefreshToken', 'BaseUserView', \
    'LoginRequiredMixin', 'set_jwt_cookies',
    ]

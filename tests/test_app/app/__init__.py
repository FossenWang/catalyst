from flask import Flask

from .views import bp, auth_jwt
from .database import db
from .config import Config

__all__ = ['create_app', 'db']



def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    auth_jwt.init_app(app)

    app.register_blueprint(bp)
    return app

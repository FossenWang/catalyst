from flask import Flask

from .views import bp
from .ext import db, jwt
from .config import Config

__all__ = ['create_app', 'db']



def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    jwt.init_app(app)

    app.register_blueprint(bp)
    return app

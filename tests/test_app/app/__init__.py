from flask import Flask

from .views import bp
from .database import db
from . import config

__all__ = ['create_app', 'db']



def create_app():
    app = Flask(__name__)
    app.config.from_object(config)
    db.init_app(app)

    app.register_blueprint(bp)
    return app

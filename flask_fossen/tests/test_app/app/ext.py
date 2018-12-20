from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

from flask_fossen.models import Model


db = SQLAlchemy(model_class=Model)
jwt = JWTManager()

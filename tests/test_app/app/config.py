import os
from flask_fossen.auth import AuthConfig

class Config(AuthConfig):
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    # Database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'test.db')
    SQLALCHEMY_MIGRATE_REPO = os.path.join(BASE_DIR, 'migrations')
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    SECRET_KEY = 'you-will-never-guess'
    DEBUG = False

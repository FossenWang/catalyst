'''
fossen's flask-based package
'''

import code
import logging

from .http import JSONResponse, register_json_error_handle
from .models import Model, SerializableModel
from .views import JSONView, Resource, ResourceList


__all__ = [
    'JSONView', 'Resource', 'ResourceList',
    'SerializableModel', 'Model',
    'register_json_error_handle', 'JSONResponse',
    'FlaskShell',
    ]


class FlaskShell:
    '''
    使用方式：
    shell = FlaskShell(app)
    shell.interact()
    调用interact方法进入Python shell模式
    自动推送app上下文
    '''
    def __init__(self, app, db=None, logging_level=None):
        self.app = app
        self.db = db
        self.logging_level = logging_level

    def interact(self, banner=None, readfunc=None, local=None, exitmsg=None):
        '进入命令行交互模式，参数与code.interact一样'
        if self.logging_level:
            logging.basicConfig()
            logging.getLogger('sqlalchemy.engine').setLevel(self.logging_level)

        # 推送Flask app上下文
        with self.app.app_context():
            local_variables = {'app': self.app}
            if self.db:
                local_variables['db'] = self.db
            if local:
                local_variables.update(local)
            code.interact(banner=banner, readfunc=readfunc, local=local_variables, exitmsg=exitmsg)

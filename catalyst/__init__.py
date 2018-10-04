from flask_sqlalchemy import Model
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship


from marshmallow import Schema


def from_attribute(obj, name):
    return obj.name


class Field:
    def __init__(self, name=None, key=None, source=from_attribute,
                 formatter=None, validator=None, required=False):
        self.name = name
        self.key = key
        self.source = source
        self.formatter = formatter
        self.validator = validator
        self.requird = required

    def extract(self, obj):
        value = self.source(obj, self.name)
        if self.formatter:
            value = self.formatter(value)
        return value

    def validate(self, data):
        value = data[self.key]
        if self.validator:
            value = self.validator(value)
        return value


class ValidationResult:
    def __init__(self, valid_data, errors, invalid_data):
        self.valid_data = valid_data
        self.is_valid = not errors
        self.errors = errors
        self.invalid_data = invalid_data

    def __str__(self):
        return '<Validation Result>'


class ValidationError(Exception):
    pass


class Catalyst:
    def __init__(self, fields):
        # 之后应用元类收集
        self.fields = fields  # type: dict

    def extract(self, obj):
        obj_dict = {}
        for field in self.fields.values():
            # key和name的默认值需要用别的办法设置
            obj_dict[field.key] = field.extract(obj)

    def validate(self, data):
        invalid_data = {}
        valid_data = {}
        errors = {}
        for field in self.fields.values():
            value = data[field.key]
            try:
                value = field.validate(value)
            except Exception as e:
                errors[field.key] = e
                invalid_data[field.key] = value
            else:
                valid_data[field.key] = value
        return ValidationResult(valid_data, errors, invalid_data)





class Article(Model):
    title = Column(String(64), nullable=False)
    content = Column(String(64), nullable=False)


class ArticleCatalyst(Catalyst):
    title = StringField(name='title', key='title_key', source=None, formatter=None, validator=None, required=True)
    content = StringField(name='content', key='content_key', source=None, formatter=None, validator=None, required=True)

article_catalyst = ArticleCatalyst()

article = Article(title='xxx', content='xxxxxx')

article_dict = article_catalyst.extract(article)

result = article_catalyst.validate(article_dict)
article = article_catalyst.create(article_dict)


# Article -> 
# {
#     'title_key': 'xxx',
#     'content_key': 'xxxxxx',
# }

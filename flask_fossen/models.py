import json
from collections import Iterable

from flask_sqlalchemy import SQLAlchemy, DefaultMeta
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer

from .validators import generate_validators_from_mapper


class ReprMixin:
    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.__str__())

    def __str__(self):
        return hex(id(self))


class Serializable:
    'Provide serializable method for the sqlalchemy Model.'
    def to_dict(self, related=[], ignore=[]):
        '''
        Convert the model to dict. By default, it converts all
        basic data attributes and ignores object attributes.

        :param ignore: optional, specifies the data attributes
        that need to be ignored, ':' to represent the data
        attributes of the related object. Such as:
        ignore = ['article_id', 'book:book_id']

        :param related: optional, specifies the related object
        to be converted to a dict, ':' to indicate the nested
        related object. Such as:
        related = ['book', 'book:author']
        '''
        results = {}
        for key, col in self.__mapper__.columns.items():
            name = col.name
            if name not in ignore:
                value = getattr(self, key)
                if isinstance(value, (int, str, float, type(None), bool)):
                    results[name] = value
                else:
                    results[name] = str(value)

        parsed_ralated = self._parse_args(related)
        parsed_ignore = self._parse_args(ignore)

        for name, relationship in self.__mapper__.relationships.items():
            if name not in parsed_ralated: continue
            if relationship.uselist:
                results[name] = [i.to_dict(
                    ignore=parsed_ignore.get(name,[]),
                    related=parsed_ralated.get(name,[]),
                    )
                    for i in getattr(self, name)]
            elif getattr(self, name):
                results[name] = getattr(self, name).to_dict(
                    ignore=parsed_ignore.get(name,[]),
                    related=parsed_ralated.get(name,[]),
                    )
            else:
                results[name] = None
        return results

    def serialize(self, related=[], ignore=[]):
        """
        Serialize objects to list or dict.
        two usages：
        1 handle one object: instance.serialize()
        2 handle objects list: Serializable.serialize([instance])

        Other params are as same as self.to_dict.
        """
        if isinstance(self, Iterable):
            results = []
            for i in self:
                assert isinstance(i, Serializable), 'The object is not Serializable.'
                if not related: related = getattr(i.__class__._meta, 'serialize_related', [])
                if not ignore: ignore = getattr(i.__class__._meta, 'serialize_ignore', [])
                results.append(i.to_dict(related=related, ignore=ignore))
            return results
        else:
            assert isinstance(self, Serializable), 'The object is not Serializable.'
            if not related: related = getattr(self.__class__._meta, 'serialize_related', [])
            if not ignore: ignore = getattr(self.__class__._meta, 'serialize_ignore', [])
            return self.to_dict(related=related, ignore=ignore)

    def to_json(self, related=[], ignore=[]):
        return json.dumps(self.serialize(related=related, ignore=ignore))

    def _parse_args(self, args):
        '''
        Parsing params to key value pairs. Key is the attribute
        that needs to be converted at present, and value is
        the parameter of the next iteration.
        '''
        parsed = {}
        for i in args:
            if ':' in i:
                temp = i.split(':', maxsplit=1)
            else:
                temp = [i, '']
            if temp[0] in parsed:
                if temp[1]: parsed.get(temp[0]).append(temp[1])
            else:
                if temp[1]: parsed[temp[0]] = [temp[1]]
                else: parsed[temp[0]] = []
        return parsed


class BaseSerializableModel(Serializable, ReprMixin):
    pass


def _validate_data(cls, data):
    '''
    Validate data and collect the error information
    if valid return (True, errors), else return (False, errors)
    '''
    errors = {}
    # ignore irrelevant data
    for name in cls._meta.default_validators:
        results = []
        value = data.get(name)
        if value is None:
            if name in cls._meta.required_fields:
                results.append('ValueError: Ensure value is not None')
        else:
            validators = cls._meta.default_validators.get(name)
            for validator in validators:
                try:
                    data[name] = validator(data[name])
                except Exception as e:
                    results.append(type(e).__name__+': '+str(e))
        if results: errors[name] = results
    return not errors, errors

def _create(cls, validated_data):
    instance = cls()
    for k, v in validated_data.items():
        if hasattr(instance, k):
            setattr(instance, k, v)
    return instance

def _update(cls, instance, validated_data):
    assert isinstance(instance, cls)
    for k, v in validated_data.items():
        if hasattr(instance, k):
            setattr(instance, k, v)
    return instance

class ValidationMeta(DefaultMeta):
    """
    Provides a method for validating the model data.
    By default, validators are automatically generated
    according to the model definition.

    Params below must be defined in an inner class Meta

    :param default_validators: optional, customize default
    validators. It must be a dict, in which key is
    model field name, and value is a list of validators.
    Example:
    default_validators = {'id': [integer_validator, ...], ...}
    
    :param extra_validators: optional, add extra validators
    to default validators.
    Same structure as default_validators.

    :param required_fields: optional, customize default
    required fields. A list of model field names.
    """
    def __init__(cls, name, bases, d):
        super().__init__(name, bases, d)
        if hasattr(cls, 'Meta'):
            meta = cls.Meta
        else:
            meta = type('Meta', (object,), {})

        if hasattr(cls, '__mapper__'):
            # Generate validators from Model definition
            validators, required = generate_validators_from_mapper(cls.__mapper__)

            if not hasattr(meta, 'default_validators'):
                meta.default_validators = validators
            else:
                for k, v in validators.items():
                    if k not in meta.default_validators:
                        meta.default_validators[k] = v

            if not hasattr(meta, 'required_fields'):
                meta.required_fields = required
            
            if hasattr(meta, 'extra_validators'):
                # Collect additional validators
                for k, v in meta.extra_validators.items():
                    meta.default_validators[k] = meta.default_validators.get(k, []) + v
            
            # Bind class method and attribute
            cls.validate_data = classmethod(_validate_data)
            cls.create = classmethod(_create)
            cls.update = classmethod(_update)
        
        cls._meta = meta


SerializableModel = declarative_base(
    cls=BaseSerializableModel,
    name='SerializableModel',
    metaclass=ValidationMeta
)


class IdMixin:
    id = Column(Integer, primary_key=True, autoincrement=True)
    def __str__(self):
        return str(self.id)


class Model(IdMixin, SerializableModel):
    __abstract__ = True


db = SQLAlchemy(model_class=SerializableModel)

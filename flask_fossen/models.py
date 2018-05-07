import json
from collections import Iterable

from flask_sqlalchemy.model import DefaultMeta
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer

from .validators import generate_validators_from_mapper


class IdMixin:
    id = Column(Integer, primary_key=True)
    def __str__(self):
        return self.id


class BaseModel:
    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.__str__())

    def __str__(self):
        return hex(id(self))


class Serializable:
    'Provide a serializable method for the sqlalchemy Model.'
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
        for k in self.__mapper__.columns.keys():
            if k not in ignore: results[k] = getattr(self, k)

        parsed_ralated = self._parse_args(related)
        parsed_ignore = self._parse_args(ignore)

        for k, v in self.__mapper__.relationships.items():
            # k为关系的属性名，v为关系对象sqlalchemy.orm.relationship
            if k not in parsed_ralated: continue
            if v.uselist:
                results[k] = [i.to_dict(
                    ignore=parsed_ignore.get(k,[]),
                    related=parsed_ralated.get(k,[]),
                    )
                    for i in getattr(self, k)]
            else:
                results[k] = getattr(self, k).to_dict(
                    ignore=parsed_ignore.get(k,[]),
                    related=parsed_ralated.get(k,[]),
                    )
        return results

    def pre_serialize(self, related=[], ignore=[]):
        """
        Pre serialize objects to list or dict.
        two usages：
        1 handle one object: serializable.pre_serialize()
        2 handle objects list: Serializable.pre_serialize([serializable])

        Other params are as same as self.to_dict.
        """
        if isinstance(self, Iterable):
            results = []
            for i in self:
                assert isinstance(i, Serializable), 'The object is not Serializable.'
                results.append(i.to_dict(related=related, ignore=ignore))
            return results
        else:
            assert isinstance(self, Serializable), 'The object is not Serializable.'
            return self.to_dict(related=related, ignore=ignore)

    def to_json(self, related=[], ignore=[]):
        return json.dumps(self.pre_serialize(related=related, ignore=ignore))

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


class BaseSerializableModel(Serializable, BaseModel):
    pass


def _validate_data(cls, data):
    '''
    Validate data and collect the error information
    if valid return (True, errors), else return (False, errors)
    '''
    errors = {}
    for k in data:
        results = []
        validators = cls._default_validators.get(k)

        if validators is None:
            results.append("TypeError: '%s' is not a field of %s" % (k, cls.__name__))
        else:
            for validator in validators:
                try:
                    data[k] = validator(k, data[k])
                except Exception as e:
                    results.append(type(e).__name__+': '+str(e))
        
        if results: errors[k] = results

    for field in cls._required_fields:
        if data.get(field) is None:
            errors[field] = ['ValueError: Ensure value is not None']

    return not errors, errors

def _create(cls, validated_data):
    return cls(**validated_data)

def _update(cls, instance, validated_data):
    assert isinstance(instance, cls)
    for k, v in validated_data.items():
        if hasattr(instance, k):
            setattr(instance, k, v)
        else:
            raise TypeError("'%s' is not a field of %s" % (k, cls.__name__))
    return instance

class ValidationMeta(DefaultMeta):
    """
    Provides a method for validating the model data.
    By default, validators are automatically generated
    according to the model definition.

    :param _default_validators: optional, customize default
    validators. It must be a dict, in which key is
    model field name, and value is a list of validators.
    Example:
    _default_validators = {'id': [integer_validator, ...], ...}
    
    :param _extra_validators: optional, add extra validators
    to default validators.
    Same structure as _default_validators.

    :param _required_fields: optional, customize default
    required fields. A list of model field names.
    """
    def __init__(cls, name, bases, d):
        super().__init__(name, bases, d)
        if hasattr(cls, '__mapper__'):
            # Generate validators from Model definition
            validators, required = generate_validators_from_mapper(cls.__mapper__)

            if not hasattr(cls, '_default_validators'):
                cls._default_validators = validators

            if not hasattr(cls, '_required_fields'):
                cls._required_fields = required

            if hasattr(cls, '_extra_validators'):
                # Collect additional validators
                for k, v in cls._extra_validators.items():
                    cls._default_validators[k] = cls._default_validators.get(k, []) + v

            # Bind class method
            cls.validate_data = classmethod(_validate_data)
            cls.create = classmethod(_create)
            cls.update = classmethod(_update)



SerializableModel = declarative_base(
    cls=BaseSerializableModel,
    name='SerializableModel',
    metaclass=ValidationMeta
)

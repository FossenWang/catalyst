from sqlalchemy import Column, Integer
import json
from collections import Iterable
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
    '为sqlalchemy的模型提供可序列化方法'
    def to_dict(self, related=[], ignore=[]):
        '''
        将模型转换为dict，默认转换所有数据属性和对象属性
        并忽略对象中包含的对象，避免循环嵌套
        ignore定义需要忽略的数据属性，':'后表示关联对象的数据属性，如ignore = ['id', 'related:id']
        related指定要转为字典的关联对象，':'后表示嵌套的关联对象，如related = ['related:related']
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
        pre serialize objects to list or dict
        two usages：
        1 handle one object: serializable.pre_serialize()
        2 handle objects list: Serializable.pre_serialize([serializable])
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
        '解析参数，按键值对分开，key为当前需要转换的属性，value为下一步迭代的参数'
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

    def is_valid(self):
        '校验数据有效性'
        return True


#class SerializableModel(Serializable, BaseModel):
#    pass


class ValidationMixin:
    """
    提供校验模型数据有效性的方法
    默认根据模型定义自动生成校验器
    通过extra_validators添加校验器
    如果要完全自己定义校验器
    则需提供default_validators
    default_validators = {'id': [integer_validator, ...], ...}
    """
    default_validators = None
    extra_validators = None
    required_fields = None

    @classmethod
    def validate_data(cls, data):
        '校验数据的有效性，有效则返回(True, errors), 无效则返回(False, errors)'
        if cls.default_validators is None:
            # 从模型定义自动生成校验器
            cls.default_validators, required = generate_validators_from_mapper(cls.__mapper__)
            if cls.required_fields is None:
                cls.required_fields = required

        if cls.extra_validators is not None:
            # 收集额外的校验器
            for k, v in cls.extra_validators.items():
                cls.default_validators[k] = v + cls.default_validators.get(k, [])
            cls.extra_validators = None

        errors = {}
        # 校验数据并收集错误信息，无错则生成实例
        for k in data:
            results = []
            for validator in cls.default_validators.get(k, []):
                try:
                    data[k] = validator(k, data[k])
                except Exception as e:
                    results.append(type(e).__name__+': '+str(e))
            if results: errors[k] = results
        for field in cls.required_fields:
            if data.get(field) is None:
                errors[field] = ['ValueError: Ensure value is not None']

        return not errors, errors

    @classmethod
    def create(cls, validated_data):
        return cls(**validated_data)

    @classmethod
    def update(cls, instance, validated_data):
        assert isinstance(instance, cls)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        return instance



class ValidationModel(ValidationMixin, BaseModel):
    pass


class SerializableModel(Serializable, ValidationModel):
    pass


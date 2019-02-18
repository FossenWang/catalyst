# catalyst
catalyst 是一个用于将数据在复杂对象和基础Python数据类型间相互转换的轻量级库

示例：
```python
from datetime import datetime
from pprint import pprint

from catalyst import Catalyst, StringField, DatetimeField, NestField


class Writer:
    def __init__(self, name):
        self.name = name


class Article:
    def __init__(self, title, content, pub_date, author):
        self.title = title
        self.content = content
        self.pub_date = pub_date
        self.author = author


class WriterCatalyst(Catalyst):
    name = StringField(min_length=0, max_length=12)

writerCatalyst = WriterCatalyst()


class ArticleCatalyst(Catalyst):
    title = StringField(min_length=1, max_length=48)
    content = StringField(min_length=1, max_length=500)
    pub_date = DatetimeField('%Y/%m/%d %H:%M:%S')
    author = NestField(writerCatalyst)

articleCatalyst = ArticleCatalyst()


fossen = Writer('fossen')
article = Article('Test', 'content', datetime(2019, 1, 1), fossen)


# Convert object to formatted data
dump_result = articleCatalyst.dump(article)
pprint(dump_result)
# {'author': {'name': 'fossen'},
#  'content': 'content',
#  'pub_date': '2019/01/01 00:00:00',
#  'title': 'Test'}


# Validate and convert raw data to valid data
load_result = articleCatalyst.load(dump_result)

pprint(type(load_result))
# <class 'catalyst.catalyst.LoadResult'>
pprint(load_result)
# {'author': LoadResult(is_valid=True, valid_data={'name': 'fossen'}),
#  'content': 'content',
#  'pub_date': datetime.datetime(2019, 1, 1, 0, 0),
#  'title': 'Test'}


# Distinguish invalid data from raw data
invalid_data = {'title': 'Test', 'pub_date': '2019/01/01', 'author': {}}

load_result = articleCatalyst.load(invalid_data)
pprint(load_result.is_valid)
# False
pprint(load_result.valid_data)
# {'title': 'Test'}
pprint(load_result.invalid_data)
# {'author': {}, 'pub_date': '2019/01/01'}
pprint(load_result.errors)
# {'author': ValidationError(LoadResult(is_valid=False, errors={'name': 'Field may not be None.'})),
#  'content': ValidationError('Field may not be None.'),
#  'pub_date': ValueError("time data '2019/01/01' does not match format '%Y/%m/%d %H:%M:%S'")}

```

---
该项目参考了 [marshmallow](https://github.com/marshmallow-code/marshmallow/) 的实现

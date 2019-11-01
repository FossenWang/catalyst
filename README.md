# catalyst
*Catalyst* is an lightweight library for converting complex datatypes to and from native Python datatypes.

```python
from datetime import datetime
from pprint import pprint

from catalyst import Catalyst, String, Datetime, NestField


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
    name = String(min_length=0, max_length=12)

writerCatalyst = WriterCatalyst()


class ArticleCatalyst(Catalyst):
    title = String(min_length=1, max_length=48)
    content = String(min_length=1, max_length=500)
    pub_date = Datetime('%Y/%m/%d %H:%M:%S')
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
# <class 'catalyst.catalyst.LoadDict'>
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
*Catalyst* is inspired by [marshmallow](https://github.com/marshmallow-code/marshmallow/).

'测试'

from unittest import TestCase

# from marshmallow import Schema

from . import Catalyst, StringField

from pprint import pprint

class Article:
    def __init__(self, title, content):
        self.title = title
        self.content = content


class ArticleCatalyst(Catalyst):
    title = StringField(max_length=12, min_length=0, name='title', key='title_key')
    content = StringField(name='content', key='content_key')


# article_dict = article_catalyst.extract(article)

# result = article_catalyst.validate(article_dict)
# article = article_catalyst.create(article_dict)


class CatalystTest(TestCase):
    def test(self):
        article_catalyst = ArticleCatalyst(fields={
            'title': ArticleCatalyst.title,
            'content': ArticleCatalyst.content,
        })
        article = Article(title='xxx', content='xxxxxx')

        article_dict = article_catalyst.extract(article)
        self.assertDictEqual(article_dict, 
            {'title_key': 'xxx', 'content_key': 'xxxxxx'})

        result = article_catalyst.validate(article_dict)
        self.assertTrue(result.is_valid)
        self.assertDictEqual(result.invalid_data, {})
        self.assertDictEqual(result.errors, {})
        self.assertDictEqual(result.valid_data, 
            {'title_key': 'xxx', 'content_key': 'xxxxxx'})

        result = article_catalyst.validate({
            'title_key': 'xxx' * 20, 'content_key': 'xxxxxx'})
        self.assertFalse(result.is_valid)
        self.assertDictEqual(result.invalid_data, {'title_key': 'xxx' * 20})
        self.assertEqual(set(result.errors), {'title_key'})
        self.assertDictEqual(result.valid_data, {'content_key': 'xxxxxx'})

        # pprint((result.errors, result.invalid_data, result.valid_data))

# Article -> 
# {
#     'title_key': 'xxx',
#     'content_key': 'xxxxxx',
# }

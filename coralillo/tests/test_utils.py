import unittest
from coralillo.utils import parse_embed


class UtilsTestCase(unittest.TestCase):

    def test_parse_embed(self):
        array = ['object']
        output = [['object', None]]
        self.assertListEqual(parse_embed(array), output)

        array = ['object.field']
        output = [['object', ['field']]]
        self.assertListEqual(parse_embed(array), output)

        array = ['object.field', 'foo', 'object.var']
        output = [['object', ['field', 'var']], ['foo', None]]
        self.assertListEqual(parse_embed(array), output)

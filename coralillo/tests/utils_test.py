from coralillo.utils import parse_embed


def test_parse_embed():
    array = ['object']
    output = [['object', None]]
    assert parse_embed(array) == output

    array = ['object.field']
    output = [['object', ['field']]]
    assert parse_embed(array) == output

    array = ['object.field', 'foo', 'object.var']
    output = [['foo', None], ['object', ['field', 'var']]]
    assert parse_embed(array) == output

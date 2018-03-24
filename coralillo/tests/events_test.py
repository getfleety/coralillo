from coralillo import Engine, Model, fields
import json

from .models import Something

def test_create_sends_message(nrm):
    p = nrm.redis.pubsub(ignore_subscribe_messages=True)
    p.psubscribe('something', 'something:*')

    thing = Something(name='the thing', abbr='TFC').save()

    messages = p.listen()

    message = next(messages)
    assert message is not None
    assert message['channel'] == b'something'
    assert json.loads(message['data'].decode('utf8')) == {
        'event': 'create',
        'data': thing.to_json(),
    }

    message = next(messages)
    assert message is not None
    assert message['channel'] == thing.key().encode()
    assert json.loads(message['data'].decode('utf8')) == {
        'event': 'create',
        'data': thing.to_json(),
    }

    p.unsubscribe()

def test_delete_sends_message(nrm):
    thing = Something(name='the thing', abbr='TFC').save()

    p = nrm.redis.pubsub(ignore_subscribe_messages=True)
    p.psubscribe('something', 'something:*')

    thing.delete()

    messages = p.listen()

    message = next(messages)
    assert message is not None
    assert message['channel'] == b'something'
    assert json.loads(message['data'].decode('utf8')) == {
        'event': 'delete',
        'data': thing.to_json(),
    }

    message = next(messages)
    assert message is not None
    assert message['channel'] == thing.key().encode()
    assert json.loads(message['data'].decode('utf8')) == {
        'event': 'delete',
        'data': thing.to_json(),
    }

    p.unsubscribe()

def test_update_sends_message(nrm):
    thing = Something(name='the thing', abbr='TFC').save()

    p = nrm.redis.pubsub(ignore_subscribe_messages=True)
    p.psubscribe('something', 'something:*')

    thing.update(name='renamed thing')

    messages = p.listen()

    message = next(messages)
    assert message is not None
    assert message['channel'] == b'something'
    data = json.loads(message['data'].decode('utf8'))
    assert data == {
        'event': 'update',
        'data': thing.to_json(),
    }

    message = next(messages)
    assert message is not None
    assert message['channel'] == thing.key().encode()
    data = json.loads(message['data'].decode('utf8'))
    assert data == {
        'event': 'update',
        'data': thing.to_json(),
    }

    assert data['data']['name'] == 'renamed thing'

    p.unsubscribe()

import unittest
from coralillo import Engine, Model, fields
import json

nrm = Engine()


class Something(Model):
    name = fields.Text()
    notify = True

    class Meta:
        engine = nrm


class EventTestCase(unittest.TestCase):

    def setUp(self):
        nrm.lua.drop(args=['*'])
        self.maxDiff = None

    def test_create_sends_message(self):
        p = nrm.redis.pubsub(ignore_subscribe_messages=True)
        p.psubscribe('something', 'something:*')

        thing = Something(name='the thing', abbr='TFC').save()

        messages = p.listen()

        message = next(messages)
        self.assertIsNotNone(message)
        self.assertEqual(message['channel'], b'something')
        self.assertDictEqual(json.loads(message['data'].decode('utf8')), {
            'event': 'create',
            'data': thing.to_json(),
        })

        message = next(messages)
        self.assertIsNotNone(message)
        self.assertEqual(message['channel'], thing.key().encode())
        self.assertDictEqual(json.loads(message['data'].decode('utf8')), {
            'event': 'create',
            'data': thing.to_json(),
        })

        p.unsubscribe()

    def test_delete_sends_message(self):
        thing = Something(name='the thing', abbr='TFC').save()

        p = nrm.redis.pubsub(ignore_subscribe_messages=True)
        p.psubscribe('something', 'something:*')

        thing.delete()

        messages = p.listen()

        message = next(messages)
        self.assertIsNotNone(message)
        self.assertEqual(message['channel'], b'something')
        self.assertDictEqual(json.loads(message['data'].decode('utf8')), {
            'event': 'delete',
            'data': thing.to_json(),
        })

        message = next(messages)
        self.assertIsNotNone(message)
        self.assertEqual(message['channel'], thing.key().encode())
        self.assertDictEqual(json.loads(message['data'].decode('utf8')), {
            'event': 'delete',
            'data': thing.to_json(),
        })

        p.unsubscribe()

    def test_update_sends_message(self):
        thing = Something(name='the thing', abbr='TFC').save()

        p = nrm.redis.pubsub(ignore_subscribe_messages=True)
        p.psubscribe('something', 'something:*')

        thing.update(name='renamed thing')

        messages = p.listen()

        message = next(messages)
        self.assertIsNotNone(message)
        self.assertEqual(message['channel'], b'something')
        data = json.loads(message['data'].decode('utf8'))
        self.assertDictEqual(data, {
            'event': 'update',
            'data': thing.to_json(),
        })

        message = next(messages)
        self.assertIsNotNone(message)
        self.assertEqual(message['channel'], thing.key().encode())
        data = json.loads(message['data'].decode('utf8'))
        self.assertDictEqual(data, {
            'event': 'update',
            'data': thing.to_json(),
        })

        self.assertEqual(data['data']['name'], 'renamed thing')

        p.unsubscribe()


if __name__ == '__main__':
    unittest.main()

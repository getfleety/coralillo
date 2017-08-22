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
        p.subscribe('something')

        fence = Something(name='the fence', abbr='TFC').save()

        p.get_message()
        message = p.get_message()

        self.assertIsNotNone(message)
        self.assertDictEqual(json.loads(message['data'].decode('utf8')), {
            'event': 'create',
            'data': fence.to_json(),
        })

        p.unsubscribe()

    def test_delete_sends_message(self):
        fence = Something(name='the fence', abbr='TFC').save()

        p = nrm.redis.pubsub(ignore_subscribe_messages=True)
        p.subscribe('something')

        fence.delete()

        p.get_message()
        message = p.get_message()

        self.assertIsNotNone(message)
        self.assertDictEqual(json.loads(message['data'].decode('utf8')), {
            'event': 'delete',
            'data': fence.to_json(),
        })

        p.unsubscribe()

    def test_update_sends_message(self):
        fence = Something(name='the fence', abbr='TFC').save()

        p = nrm.redis.pubsub(ignore_subscribe_messages=True)
        p.subscribe('something')

        fence.update(name='renamed fence')

        p.get_message()
        message = p.get_message()

        self.assertIsNotNone(message)
        data = json.loads(message['data'].decode('utf8'))
        self.assertDictEqual(data, {
            'event': 'update',
            'data': fence.to_json(),
        })

        self.assertEqual(data['data']['attributes']['name'], 'renamed fence')

        p.unsubscribe()


if __name__ == '__main__':
    unittest.main()

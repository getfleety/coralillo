import unittest
from .lua import drop
import json


class EventTestCase(unittest.TestCase):

    def setUp(self):
        drop(args=['*'])
        self.maxDiff = None
        self.app.config['ORGANIZATION'] = 'testing'

    def test_create_sends_message(self):
        p = redis.pubsub(ignore_subscribe_messages=True)
        p.subscribe('testing:geofence')

        fence = Geofence(name='the fence', abbr='TFC').save()

        p.get_message() # Consume the subscribe message
        message = p.get_message()

        self.assertIsNotNone(message)
        self.assertDictEqual(json.loads(message['data']), {
            'event': 'create',
            'data': fence.to_json(),
        })

        p.unsubscribe()

    def test_delete_sends_message(self):
        fence = Geofence(name='the fence', abbr='TFC').save()

        p = redis.pubsub(ignore_subscribe_messages=True)
        p.subscribe('testing:geofence')

        fence.delete()

        p.get_message()
        message = p.get_message()

        self.assertIsNotNone(message)
        self.assertDictEqual(json.loads(message['data']), {
            'event': 'delete',
            'data': fence.to_json(),
        })

        p.unsubscribe()

    def test_update_sends_message(self):
        fence = Geofence(name='the fence', abbr='TFC').save()

        p = redis.pubsub(ignore_subscribe_messages=True)
        p.subscribe('testing:geofence')

        fence.update(name='renamed fence')

        p.get_message()
        message = p.get_message()

        self.assertIsNotNone(message)
        data = json.loads(message['data'])
        self.assertDictEqual(data, {
            'event': 'update',
            'data': fence.to_json(),
        })

        self.assertEqual(data['data']['attributes']['name'], 'renamed fence')

        p.unsubscribe()

from .lua import drop
import unittest


class RelationTestCase(unittest.TestCase):

    def setUp(self):
# TODO remove when extracting the ORM
        drop(args=['*'])
        self.app = app
        self.app.config['ORGANIZATION'] = 'testing'
        self.pwd = 'bcrypt$$2b$12$gWQweaiLPJr2OHSPOshyQe3zmnSAPGv2pA.PwOIuxZ3ylvLMN7h6C'

    def test_relation(self):
        org = Organization(
            name      = 'Testing Inc',
            subdomain = 'testing',
        ).save()

        user = User(
            name      = 'Sam',
            last_name = 'Smith',
            email     = 'sam@testing.com',
            password  = self.pwd,
        ).save()
        user.proxy.orgs.set([org])

        self.assertEqual(user.orgs[0].id, org.id)
        self.assertTrue(redis.sismember('user:{}:srel_orgs'.format(user.id), org.id))

        same = User.get(user.id)
        same.proxy.orgs.fill()

        self.assertEqual(same.orgs[0].id, org.id)
        self.assertEqual(same.to_json()['relations']['orgs'][0]['attributes']['subdomain'], 'testing')

    def test_delete_with_related(self):
        pos1 = Position(lat=-100, lon=20).save()
        pos2 = Position(lat=-100, lon=20).save()

        self.device = Device(
            code = '1234',
        ).save()
        self.device.proxy.location_history.set([pos1, pos2])

        self.device.delete()

        self.assertIsNone(Position.get(pos1.id))
        self.assertIsNone(Position.get(pos2.id))

    def test_many_to_many_relationship(self):
        u1 = User(name='u1', last_name='l1', email='1@a.ly', password=self.pwd).save()
        u2 = User(name='u2', last_name='l2', email='2@a.ly', password=self.pwd).save()
        o1 = Organization(name='o1', subdomain='o1').save()
        o2 = Organization(name='o2', subdomain='o2').save()

        # test adding a relationship creates the inverse
        u1.proxy.orgs.set([o1, o2])

        o1.proxy.users.fill()
        o2.proxy.users.fill()

        self.assertTrue(type(o1.users) == list)
        self.assertTrue(type(o2.users) == list)

        self.assertEqual(len(o1.users), 1)
        self.assertEqual(len(o2.users), 1)

        self.assertEqual(o1.users[0].name, 'u1')
        self.assertEqual(o2.users[0].name, 'u1')

        u2.proxy.orgs.set([o2])

        o1.proxy.users.fill()
        o2.proxy.users.fill()

        self.assertTrue(type(o1.users) == list)
        self.assertTrue(type(o2.users) == list)

        self.assertEqual(len(o1.users), 1)
        self.assertEqual(len(o2.users), 2)

        o2.users.sort(key=lambda x:x.name)

        self.assertEqual(o1.users[0].name, 'u1')
        self.assertEqual(o2.users[0].name, 'u1')
        self.assertEqual(o2.users[1].name, 'u2')

        # test deleting an object deletes the relationship in the related

        u1.delete()

        o1.proxy.users.fill()
        o2.proxy.users.fill()

        self.assertTrue(type(o1.users) == list)
        self.assertTrue(type(o2.users) == list)

        self.assertEqual(len(o1.users), 0)
        self.assertEqual(len(o2.users), 1)

    def test_querying_related(self):
        o1 = Organization(name='o1', subdomain='o1').save()
        u1 = User(name='u1', last_name='l1', email='1@a.ly', password=self.pwd).save()
        u2 = User(name='u2', last_name='l2', email='2@a.ly', password=self.pwd).save()
        u1.proxy.orgs.set([o1])

        self.assertTrue(u1 in o1.proxy.users)
        self.assertFalse(u2 in o1.proxy.users)

    def test_foreign_key(self):
        fleet = Fleet(name='fleet', abbr='FLT').save()
        dev = Device(code='dev').save()
        dev.proxy.fleet.set(fleet)

        dev.proxy.fleet.fill()
        fleet.proxy.devices.fill()

        self.assertIsNotNone(dev.fleet)
        self.assertEqual(dev.fleet.id, fleet.id)

        self.assertTrue(type(fleet.devices) == list)
        self.assertEqual(len(fleet.devices), 1)
        self.assertEqual(fleet.devices[0].id, dev.id)

        dev.delete()

        dev.proxy.fleet.fill()
        fleet.proxy.devices.fill()

        self.assertTrue(type(fleet.devices) == list)
        self.assertEqual(len(fleet.devices), 0)

    def test_foreign_key_inverse(self):
        dev = Device(code='dev').save()
        fleet = Fleet(name='fleet', abbr='FLT').save()
        fleet.proxy.devices.set([dev])

        dev.proxy.fleet.fill()
        fleet.proxy.devices.fill()

        self.assertIsNotNone(dev.fleet)
        self.assertEqual(dev.fleet.id, fleet.id)

        self.assertTrue(type(fleet.devices) == list)
        self.assertEqual(len(fleet.devices), 1)
        self.assertEqual(fleet.devices[0].id, dev.id)

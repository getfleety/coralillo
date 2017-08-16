from fleety import app, redis
from fleety.db.models import User, Organization
from fleety.db.models.bounded import Fleet, Device
from fleety.db.orm import datamodel
from fleety.db.orm.lua import drop
import unittest


class ModelTestCase(unittest.TestCase):

    def setUp(self):
# TODO remove this before migrate to own orm package
        drop(args=['*'])
        self.pwd = 'bcrypt$$2b$12$gWQweaiLPJr2OHSPOshyQe3zmnSAPGv2pA.PwOIuxZ3ylvLMN7h6C'
        self.app = app
        self.app.config['ORGANIZATION'] = 'testing'

    def test_create_user(self):
        user = User(
            name      = 'John',
            last_name = 'Doe',
            email     = 'johndoe@gmail.com',
            password  = self.pwd,
            is_active = False,
        ).save()

        self.assertEqual(user.name, 'John')
        self.assertEqual(user.last_name, 'Doe')
        self.assertEqual(user.email, 'johndoe@gmail.com')
        self.assertNotEqual(user.password, '123456')
        self.assertFalse(user.is_active)

        self.assertTrue(redis.sismember('user:members', user.id))

    def test_retrieve_user_by_id(self):
        user = User(
            name      = 'Carla',
            last_name = 'Morrison',
            email     = 'carla@morrison.com',
            password  = self.pwd,
        ).save()

        read_user = User.get(user.id)

        self.assertEqual(read_user.name, user.name)
        self.assertEqual(read_user.last_name, user.last_name)
        self.assertEqual(read_user.email, user.email)
        self.assertEqual(read_user.password, user.password)

    def test_retrieve_by_index(self):
        admin = User(
            name      = 'Admin',
            last_name = 'Wayers',
            email     = 'admin@testing.com',
            password  = self.pwd,
        ).save()

        user = User.get_by('email', 'admin@testing.com')

        self.assertTrue(user == admin)

    def test_update_keep_index(self):
        fleet = Fleet(abbr='FOO', name='the fleet').save()

        fleet.update(abbr='FOO', name='updated name')

        self.assertEqual(fleet.abbr, 'FOO')
        self.assertEqual(fleet.name, 'updated name')

        self.assertEqual(datamodel.debyte_string(redis.hget('testing:fleet:index_abbr', 'FOO')), fleet.id)

    def test_update_changes_index(self):
        fleet = Fleet(abbr='FOO', name='the fleet').save()

        fleet.update(abbr='VAR', name='the fleet')

        self.assertEqual(fleet.abbr, 'VAR')
        self.assertEqual(fleet.name, 'the fleet')

        self.assertEqual(datamodel.debyte_string(redis.hget('testing:fleet:index_abbr', 'VAR')), fleet.id)
        self.assertIsNone(redis.hget('testing:fleet:index_abbr', 'FOO'))

    def test_get(self):
        org = Organization(name='Org 1', subdomain='org1').save()
        got = Organization.get(org.id)

        self.assertTrue(org == got)

    def test_get_all(self):
        org1 = Organization(name='Org 1', subdomain='org1').save()
        org2 = Organization(name='Org 2', subdomain='org2').save()

        allitems = Organization.get_all()

        allitems.sort(key=lambda x: x.name)

        item1 = allitems[0]
        item2 = allitems[1]

        self.assertEqual(item1, org1)
        self.assertEqual(item2, org2)

    def test_bounded_model(self):
        dev = Device(
            code = 'foo',
        ).save()

        self.assertFalse(redis.exists('device:'+dev.id))
        self.assertTrue(redis.exists('testing:device:'+dev.id))
        self.assertTrue(redis.hexists('testing:device:'+dev.id, 'code'))

    def test_create_bounded(self):
        dev = Device(
            code = 'foo',
        ).save()

        self.assertTrue(redis.sismember('testing:device:members', dev.id))

    def test_delete(self):
        dev = Device(
            code = 'foo',
        ).save()

        self.assertIsNotNone(Device.get(dev.id))

        dev.delete()

        self.assertIsNone(Device.get(dev.id))
        self.assertFalse(redis.sismember('testing:device:members', dev.id))

    def test_delete_index(self):
        fleet = Fleet(abbr='FOO', name='fleet').save()

        self.assertEqual(datamodel.debyte_string(redis.hget('testing:fleet:index_abbr', 'FOO')), fleet.id)

        fleet.delete()

        self.assertIsNone(redis.hget('testing:fleet:index_abbr', 'FOO'))

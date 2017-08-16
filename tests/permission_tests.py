from fleety import redis
from fleety.db.orm.lua import drop
from fleety.db.orm import Model, fields
from fleety.db.orm.auth import PermissionHolder
import unittest


class User(Model, PermissionHolder):
    name = fields.Text()


class PermissionTestCase(unittest.TestCase):

    def setUp(self):
        drop(args=['*'])
        self.pwd = 'bcrypt$$2b$12$gWQweaiLPJr2OHSPOshyQe3zmnSAPGv2pA.PwOIuxZ3ylvLMN7h6C'
        self.user = User(
            name      = 'juan',
        ).save()
        self.allow_key = self.user.allow_key()

    def test_add_permissions(self):
        self.user.allow('a:b:c')
        self.assertTrue(redis.sismember(self.allow_key, 'a:b:c'))

    def test_add_ignores_when_has_parent(self):
        self.user.allow('a')
        self.user.allow('a:b')
        self.user.allow('a:b:c')

        self.assertTrue(redis.sismember(self.allow_key, 'a'))
        self.assertFalse(redis.sismember(self.allow_key, 'a:b'))
        self.assertFalse(redis.sismember(self.allow_key, 'a:b:c'))

        self.user.allow('foo:var')
        self.user.allow('foo:var:log')
        self.assertFalse(redis.sismember(self.allow_key, 'foo'))
        self.assertTrue(redis.sismember(self.allow_key, 'foo:var'))
        self.assertFalse(redis.sismember(self.allow_key, 'foo:var:log'))

    def test_revoke_permission(self):
        self.user.allow('a:b')
        self.user.revoke('a:b')

        self.assertFalse(redis.sismember(self.allow_key, 'a:b'))

    def test_check_permission_inheritance(self):
        self.user.allow('a:b')

        self.assertTrue(self.user.is_allowed('a:b'))
        self.assertTrue(self.user.is_allowed('a:b:c'))

        self.assertFalse(self.user.is_allowed('a'))
        self.assertFalse(self.user.is_allowed('a:d'))

    def test_can_carry_tail(self):
        self.user.allow('org:fleet:view')

        self.assertFalse(self.user.is_allowed('org:fleet:somefleet:view'))
        self.assertTrue(self.user.is_allowed('org:fleet:somefleet', 'view'))

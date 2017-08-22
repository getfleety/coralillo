from coralillo import Model, fields, Engine
from coralillo.auth import PermissionHolder
import unittest

nrm = Engine()


class User(Model, PermissionHolder):
    name = fields.Text()

    class Meta:
        engine = nrm


class PermissionTestCase(unittest.TestCase):

    def setUp(self):
        nrm.lua.drop(args=['*'])
        self.user = User(
            name      = 'juan',
        ).save()
        self.allow_key = self.user.allow_key()

    def test_add_permissions(self):
        self.user.allow('a:b:c', nrm)
        self.assertTrue(nrm.redis.sismember(self.allow_key, 'a:b:c'))

    def test_add_ignores_when_has_parent(self):
        self.user.allow('a', nrm)
        self.user.allow('a:b', nrm)
        self.user.allow('a:b:c', nrm)

        self.assertTrue(nrm.redis.sismember(self.allow_key, 'a'))
        self.assertFalse(nrm.redis.sismember(self.allow_key, 'a:b'))
        self.assertFalse(nrm.redis.sismember(self.allow_key, 'a:b:c'))

        self.user.allow('foo:var', nrm)
        self.user.allow('foo:var:log', nrm)
        self.assertFalse(nrm.redis.sismember(self.allow_key, 'foo'))
        self.assertTrue(nrm.redis.sismember(self.allow_key, 'foo:var'))
        self.assertFalse(nrm.redis.sismember(self.allow_key, 'foo:var:log'))

    def test_revoke_permission(self):
        self.user.allow('a:b', nrm)
        self.user.revoke('a:b', nrm)

        self.assertFalse(nrm.redis.sismember(self.allow_key, 'a:b'))

    def test_check_permission_inheritance(self):
        self.user.allow('a:b', nrm)

        self.assertTrue(self.user.is_allowed('a:b', nrm))
        self.assertTrue(self.user.is_allowed('a:b:c', nrm))

        self.assertFalse(self.user.is_allowed('a', nrm))
        self.assertFalse(self.user.is_allowed('a:d', nrm))

    def test_can_carry_tail(self):
        self.user.allow('org:fleet:view', nrm)

        self.assertFalse(self.user.is_allowed('org:fleet:somefleet:view', nrm))
        self.assertTrue(self.user.is_allowed('org:fleet:somefleet', nrm, tail='view'))


if __name__ == '__main__':
    unittest.main()

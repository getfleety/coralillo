from coralillo import Model, BoundedModel, fields, Engine
from coralillo.auth import PermissionHolder
import unittest

nrm = Engine()


class User(Model, PermissionHolder):
    name = fields.Text()

    class Meta:
        engine = nrm

class Pet(BoundedModel):
    name = fields.Text()

    class Meta:
        engine = nrm

    @classmethod
    def prefix(cls):
        return 'bound'


class PermissionTestCase(unittest.TestCase):

    def setUp(self):
        nrm.lua.drop(args=['*'])
        self.user = User(
            name      = 'juan',
        ).save()
        self.allow_key = self.user.allow_key()

    def test_allow_key(self):
        self.user.allow('a')

        self.assertTrue(nrm.redis.exists('user:{}:allow'.format(self.user.id)))

    def test_add_permissions(self):
        self.user.allow('a:b:c')
        self.assertTrue(nrm.redis.sismember(self.allow_key, 'a:b:c'))

    def test_add_ignores_when_has_parent(self):
        self.user.allow('a')
        self.user.allow('a:b')
        self.user.allow('a:b:c')

        self.assertTrue(nrm.redis.sismember(self.allow_key, 'a'))
        self.assertFalse(nrm.redis.sismember(self.allow_key, 'a:b'))
        self.assertFalse(nrm.redis.sismember(self.allow_key, 'a:b:c'))

        self.user.allow('foo:var')
        self.user.allow('foo:var:log')
        self.assertFalse(nrm.redis.sismember(self.allow_key, 'foo'))
        self.assertTrue(nrm.redis.sismember(self.allow_key, 'foo:var'))
        self.assertFalse(nrm.redis.sismember(self.allow_key, 'foo:var:log'))

    def test_add_deletes_lower(self):
        self.user.allow('a:b/v')
        self.user.allow('a/v')

        self.assertSetEqual(self.user.get_perms(), set(['a/v']))

    def test_revoke_permission(self):
        self.user.allow('a:b')
        self.user.revoke('a:b')

        self.assertFalse(nrm.redis.sismember(self.allow_key, 'a:b'))

    def test_check_permission_inheritance(self):
        self.user.allow('a:b')

        self.assertTrue(self.user.is_allowed('a:b'))
        self.assertTrue(self.user.is_allowed('a:b:c'))

        self.assertFalse(self.user.is_allowed('a'))
        self.assertFalse(self.user.is_allowed('a:d'))

    def test_can_carry_restrict(self):
        self.user.allow('org:fleet/view')

        self.assertTrue(self.user.is_allowed('org:fleet:somefleet/view'))

    def test_permission_key(self):
        self.assertEqual(self.user.permission(), 'user:{}'.format(self.user.id))
        self.assertEqual(self.user.permission(restrict='view'), 'user:{}/view'.format(self.user.id))

    def test_minor_ignored_if_mayor(self):
        self.user.allow('org:fleet/view')
        self.user.allow('org:fleet:325234/view')

        self.assertSetEqual(self.user.get_perms(), set(['org:fleet/view']))

    def test_perm_framework_needs_strings(self):
        with self.assertRaises(AssertionError):
            self.user.allow(User)

        with self.assertRaises(AssertionError):
            self.user.is_allowed(User)

        with self.assertRaises(AssertionError):
            self.user.revoke(User)

    def test_permission_function(self):
        self.assertEqual(self.user.permission(), 'user:{}'.format(self.user.id))
        self.assertEqual(self.user.permission('eat'), 'user:{}/eat'.format(self.user.id))

        pet = Pet(name='doggo').save()
        self.assertEqual(pet.permission(), 'bound:pet:{}'.format(pet.id))
        self.assertEqual(pet.permission('walk'), 'bound:pet:{}/walk'.format(pet.id))

    def test_delete_user_deletes_permission_bag(self):
        self.user.allow('foo')

        self.assertTrue(nrm.redis.exists('user:{}:allow'.format(self.user.id)))

        self.user.delete()
        self.assertFalse(nrm.redis.exists('user:{}:allow'.format(self.user.id)))


if __name__ == '__main__':
    unittest.main()

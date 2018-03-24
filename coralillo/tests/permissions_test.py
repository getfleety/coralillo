from coralillo import Model, BoundedModel, fields, Engine
import pytest

from .models import Bunny

def test_allow_key(nrm, user):
    user.allow('a')

    assert nrm.redis.exists('user:{}:allow'.format(user.id))

def test_add_permissions(nrm, user):
    user.allow('a:b:c')
    assert nrm.redis.sismember(user.allow_key(), 'a:b:c')

def test_add_ignores_when_has_parent(nrm, user):
    user.allow('a')
    user.allow('a:b')
    user.allow('a:b:c')

    assert nrm.redis.sismember(user.allow_key(), 'a')
    assert not nrm.redis.sismember(user.allow_key(), 'a:b')
    assert not nrm.redis.sismember(user.allow_key(), 'a:b:c')

    user.allow('foo:var')
    user.allow('foo:var:log')
    assert not nrm.redis.sismember(user.allow_key(), 'foo')
    assert nrm.redis.sismember(user.allow_key(), 'foo:var')
    assert not nrm.redis.sismember(user.allow_key(), 'foo:var:log')

def test_add_deletes_lower(nrm, user):
    user.allow('a:b/v')
    user.allow('a/v')

    assert user.get_perms() == set(['a/v'])

def test_revoke_permission(nrm, user):
    user.allow('a:b')
    user.revoke('a:b')

    assert not nrm.redis.sismember(user.allow_key(), 'a:b')

def test_check_permission_inheritance(nrm, user):
    user.allow('a:b')

    assert user.is_allowed('a:b')
    assert user.is_allowed('a:b:c')

    assert not user.is_allowed('a')
    assert not user.is_allowed('a:d')

def test_can_carry_restrict(nrm, user):
    user.allow('org:fleet/view')

    assert user.is_allowed('org:fleet:somefleet/view')

def test_permission_key(nrm, user):
    assert user.permission() == 'user:{}'.format(user.id)
    assert user.permission(restrict='view') == 'user:{}/view'.format(user.id)

def test_minor_ignored_if_mayor(nrm, user):
    user.allow('org:fleet/view')
    user.allow('org:fleet:325234/view')

    assert user.get_perms() == set(['org:fleet/view'])

def test_perm_framework_needs_strings(nrm, user):
    class User: pass

    with pytest.raises(AssertionError):
        user.allow(User)

    with pytest.raises(AssertionError):
        user.is_allowed(User)

    with pytest.raises(AssertionError):
        user.revoke(User)

def test_permission_function(nrm, user):
    assert user.permission() == 'user:{}'.format(user.id)
    assert user.permission('eat') == 'user:{}/eat'.format(user.id)

    bunny = Bunny(name='doggo').save()
    assert bunny.permission() == 'bound:bunny:{}'.format(bunny.id)
    assert bunny.permission('walk') == 'bound:bunny:{}/walk'.format(bunny.id)

def test_delete_user_deletes_permission_bag(nrm, user):
    user.allow('foo')

    assert nrm.redis.exists('user:{}:allow'.format(user.id))

    user.delete()
    assert not nrm.redis.exists('user:{}:allow'.format(user.id))

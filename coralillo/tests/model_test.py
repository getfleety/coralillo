from collections import Iterable
from coralillo.datamodel import debyte_string
from coralillo.errors import ModelNotFoundError
from .models import House, Table, Ship, Tenanted, SideWalk, Pet
import pytest

def test_create_user(nrm):
    user = Table(
        name      = 'John',
    ).save()

    assert user.name == 'John'

    assert nrm.redis.sismember('table:members', user.id)
    assert nrm.redis.hget('table:{}:obj'.format(user.id), 'name') == b'John'

def test_retrieve_user_by_id(nrm):
    carla = Table( name = 'Carla',).save()
    roberta = Table( name = 'Roberta',).save()

    read_user = Table.get(carla.id)

    assert read_user.name == carla.name

def test_retrieve_by_index(nrm):
    titan = Ship(name='te trece', code = 'T13',).save()
    atlan = Ship(name='te catorce', code = 'T14',).save()

    found_ship = Ship.get_by('code', 'T13')

    assert found_ship is not None
    assert titan == found_ship

def test_filter(nrm):
    with pytest.raises(AttributeError) as excinfo:
        Pet.q().filter(legs__in=(3, 4))

    assert str(excinfo.value) == 'Model Pet does not have field legs'

    with pytest.raises(AttributeError) as excinfo:
        Pet.q().filter(name__foo=True)

    assert str(excinfo.value) == 'Filter foo does not exist'

    pets = [
        Pet(name='bc').save(), # 0
        Pet(name='bd').save(), # 1
        Pet(name='cd').save(), # 2
    ]

    assert isinstance(Pet.q(), Iterable)

    res = list(map(
        lambda x:x.id,
        Pet.q().filter(name__startswith='b', name__endswith='d')
    ))

    assert res == [pets[1].id]

    res = list(map(
        lambda x:x.id,
        Pet.q().filter(name__startswith='b').filter(name__endswith='d')
    ))

    assert res == [pets[1].id]

def test_update_keep_index(nrm):
    ship = Ship(name='the ship', code='TS').save()

    ship.update(name='updated name')

    assert ship.code == 'TS'
    assert ship.name == 'updated name'

    assert debyte_string(nrm.redis.hget('ship:index_code', 'TS')) == ship.id

def test_update_changes_index(nrm):
    ship = Ship(code='THECODE').save()

    ship.update(code='NEWCODE')

    assert ship.code == 'NEWCODE'

    assert debyte_string(nrm.redis.hget('ship:index_code', 'NEWCODE')) == ship.id
    assert nrm.redis.hget('ship:index_code', 'THECODE') is None

def test_get(nrm):
    org = Table(name='Juan').save()
    got = Table.get(org.id)

    assert org == got

def test_get_all(nrm):
    p1 = Table(name='Juan').save()
    p2 = Table(name='Pepe').save()

    allitems = Table.get_all()

    allitems.sort(key=lambda x: x.name)

    item1 = allitems[0]
    item2 = allitems[1]

    assert item1 == p1
    assert item2 == p2

def test_bounded_model(nrm):
    dev = Tenanted(
        name = 'foo',
    ).save()

    assert not nrm.redis.exists('tenanted:'+dev.id)
    assert nrm.redis.exists('testing:tenanted:{}:obj'.format(dev.id))
    assert nrm.redis.hget('testing:tenanted:{}:obj'.format(dev.id), 'name') == b'foo'
    assert nrm.redis.sismember('testing:tenanted:members', dev.id)

def test_delete(nrm):
    dev = Tenanted(
        code = 'foo',
    ).save()

    assert Tenanted.get(dev.id) is not None

    dev.delete()

    assert Tenanted.get(dev.id) is None
    assert not nrm.redis.sismember('testing:tenanted:members', dev.id)

def test_delete_index(nrm):
    ship = Ship(code='A12').save()

    assert debyte_string(nrm.redis.hget('ship:index_code', 'A12')) == ship.id

    ship.delete()

    assert not nrm.redis.hexists('ship:index_code', 'A12')

def test_is_object_key(nrm):
    ship = Ship(code='A12').save()

    assert Ship.is_object_key(ship.key())

def test_fqn(nrm):
    ship = Ship(code='A12').save()

    assert ship.fqn() == 'ship:{}'.format(ship.id)

def test_model_table_conversion(nrm):
    sw = SideWalk(name='foo').save()

    assert nrm.redis.exists('side_walk:members')
    assert nrm.redis.exists('side_walk:{}:obj'.format(sw.id))

def test_object_count(nrm):
    sw1 = SideWalk(name='1').save()
    assert SideWalk.count() == 1

    sw2 = SideWalk(name='2').save()
    assert SideWalk.count() == 2

    sw1.delete()
    assert SideWalk.count() == 1

def test_get_or_exception(nrm):
    with pytest.raises(ModelNotFoundError):
        SideWalk.get_or_exception('nonsense')

    with pytest.raises(ModelNotFoundError):
        Ship.get_by_or_exception('code', 'nonsense')

def test_recover_none_int(nrm):
    h = House.validate()
    h.save()

    h_rec = House.get(h.id)
    assert h.number is None

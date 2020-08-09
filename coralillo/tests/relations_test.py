from collections.abc import Iterable
from datetime import datetime

from .models import Pet, Person, UnattachedPerson, Driver, Car, Admin, Log


def test_relation(nrm):
    org = Car(
        name='Testing Inc',
    ).save()

    user = Driver(
        name='Sam',
    ).save()

    user.cars.set([org])
    user.save()

    assert user.cars.count() == 1

    assert user.cars.all()[0].id == org.id
    assert nrm.redis.sismember('driver:{}:srel_cars'.format(user.id), org.id)

    same = Driver.get(user.id)
    same.cars.all()

    assert same.cars.all()[0].id == org.id
    assert same.to_json(include=['cars'])['cars'][0]['name'] == 'Testing Inc'


def test_delete_cascade(nrm):
    doggo = Pet(name='doggo').save()
    catto = Pet(name='catto').save()

    owner = Person(
        name='John',
    ).save()
    owner.pets.set([doggo, catto])

    assert doggo in owner.pets
    assert catto in owner.pets

    owner.delete()

    assert Pet.get(doggo.id) is None
    assert Pet.get(catto.id) is None


def test_delete_preserves_related_no_cascade(nrm):
    doggo = Pet(name='doggo').save()
    catto = Pet(name='catto').save()

    owner = UnattachedPerson(
        name='John',
    ).save()
    owner.pets.set([doggo, catto])

    assert doggo in owner.pets
    assert catto in owner.pets

    owner.delete()

    assert Pet.get(doggo.id).name == 'doggo'
    assert Pet.get(catto.id).name == 'catto'


def test_many_to_many_relationship(nrm):
    u1 = Driver(name='u1').save()
    u2 = Driver(name='u2').save()
    o1 = Car(name='o1').save()
    o2 = Car(name='o2').save()

    # test adding a relationship creates the inverse
    u1.cars.set([o1, o2])
    u1.save()

    o1drivers = o1.drivers.all()
    o2drivers = o2.drivers.all()

    assert type(o1drivers) == list
    assert type(o2drivers) == list

    assert len(o1drivers) == 1
    assert len(o2drivers) == 1

    assert o1drivers[0].name == 'u1'
    assert o2drivers[0].name == 'u1'

    u2.cars.set([o2])

    o1drivers = o1.drivers.all()
    o2drivers = o2.drivers.all()

    assert type(o1drivers) == list
    assert type(o2drivers) == list

    assert len(o1drivers) == 1
    assert len(o2drivers) == 2

    o2drivers.sort(key=lambda x: x.name)

    assert o1drivers[0].name == 'u1'
    assert o2drivers[0].name == 'u1'
    assert o2drivers[1].name == 'u2'

    # test deleting an object deletes the relationship in the related

    u1.delete()

    o1drivers = o1.drivers.all()
    o2drivers = o2.drivers.all()

    assert type(o1drivers) == list
    assert type(o2drivers) == list

    assert len(o1drivers) == 0
    assert len(o2drivers) == 1


def test_querying_related(nrm):
    o1 = Car(name='o1').save()
    u1 = Driver(name='u1').save()
    u2 = Driver(name='u2').save()
    u1.cars.set([o1])

    assert u1 in o1.drivers
    assert u2 not in o1.drivers


def test_can_filter_related(nrm):
    p = Person(name='Juan').save()

    pets = [
        Pet(name='bc').save(),  # 0
        Pet(name='bd').save(),  # 1
        Pet(name='cd').save(),  # 2
    ]

    p.pets.set(pets)

    assert isinstance(p.pets.q().filter(name__startswith='pa'), Iterable)

    res = list(map(
        lambda x: x.id,
        p.pets.q().filter(name__startswith='b', name__endswith='d')
    ))

    assert res == [pets[1].id]

    res = list(map(
        lambda x: x.id,
        p.pets.q().filter(name__startswith='b').filter(name__endswith='d')
    ))

    assert res == [pets[1].id]


def test_foreign_key(nrm):
    owner = Person(name='John').save()
    pet = Pet(name='doggo').save()

    pet.owner.set(owner)
    ownerpets = owner.pets.all()

    assert pet.owner.get() is not None
    assert pet.owner.get().id == owner.id

    ownerpets = owner.pets.all()

    assert type(ownerpets) == list
    assert len(ownerpets) == 1
    assert ownerpets[0].id == pet.id

    pet.delete()

    ownerpets = owner.pets.all()

    assert type(ownerpets) == list
    assert len(ownerpets) == 0


def test_foreign_key_inverse(nrm):
    pet = Pet(name='doggo').save()
    owner = Person(name='John').save()
    owner.pets.set([pet])

    petowner = pet.owner.get()
    ownerpets = owner.pets.all()

    assert petowner is not None
    assert petowner.id == owner.id

    assert type(ownerpets) == list
    assert len(ownerpets) == 1
    assert ownerpets[0].id == pet.id


def test_delete_relation(nrm):
    c1 = Car().save()
    c2 = Car().save()

    d1 = Driver().save()

    d1.cars.set([c1, c2])

    assert c1 in d1.cars
    assert c2 in d1.cars
    assert d1 in c1.drivers
    assert d1 in c2.drivers

    d1.cars.remove(c1)

    assert c1 not in d1.cars
    assert c2 in d1.cars
    assert d1 not in c1.drivers
    assert d1 in c2.drivers


def test_clear(nrm):
    owner = Person(name='Juan').save()

    pets = [
        Pet(name='doggo').save(),
        Pet(name='catto').save(),
    ]

    owner.pets.set(pets)

    assert owner.pets.count() == 2

    assert pets[0].owner.get() is not None
    assert pets[1].owner.get() is not None

    owner.pets.clear()

    assert owner.pets.count() == 0

    assert pets[0].owner.get() is None
    assert pets[1].owner.get() is None


def test_get_relation(nrm):
    c1 = Car().save()
    c2 = Car().save()

    d1 = Driver().save()

    d1.cars.set([c1, c2])

    cars = d1.cars.all()

    orig = sorted([c1, c2], key=lambda c: c.id)
    cars = sorted(cars, key=lambda c: c.id)

    assert orig == cars


def test_get_foreignid_relation(nrm):
    pet = Pet().save()
    owner = Person().save()
    owner.pets.add(pet)

    assert pet.owner.get().id == owner.id

    owner.pets.remove(pet)

    assert pet.owner.get() is None


def test_sorted_set_relation(nrm):
    owner = Admin(name='Juan').save()

    logs = [
        Log(date=datetime(2020, 1, 1), data='1').save(),
        Log(date=datetime(2020, 1, 1), data='1').save(),
        Log(date=datetime(2020, 1, 1), data='1').save(),
    ]

    owner.logs.set(logs[:-1])
    owner.logs.add(logs[-1])

    assert owner.logs.count() == 3

    for old, new in zip(logs, owner.logs.all()):
        assert old.id == new.id

    for log in logs:
        assert log in owner.logs

    owner.delete()

    for log in logs:
        assert log.owner.get() is None

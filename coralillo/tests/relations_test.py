from collections import Iterable
from .models import Pet, Person, Driver, Car


def test_relation(nrm):
    org = Car(
        name      = 'Testing Inc',
    ).save()

    user = Driver(
        name      = 'Sam',
    ).save()
    user.proxy.cars.set([org])

    assert user.proxy.cars.count() == 1

    assert user.cars[0].id == org.id
    assert nrm.redis.sismember('driver:{}:srel_cars'.format(user.id), org.id)

    same = Driver.get(user.id)
    same.proxy.cars.fill()

    assert same.cars[0].id == org.id
    assert same.to_json(embed=['cars'])['cars'][0]['name'] == 'Testing Inc'

def test_delete_with_related(nrm):
    doggo = Pet(name='doggo').save()
    catto = Pet(name='catto').save()

    owner = Person(
        name = 'John',
    ).save()
    owner.proxy.pets.set([doggo, catto])

    assert doggo in owner.proxy.pets
    assert catto in owner.proxy.pets

    owner.delete()

    assert Pet.get(doggo.id) is None
    assert Pet.get(catto.id) is None

def test_many_to_many_relationship(nrm):
    u1 = Driver(name='u1').save()
    u2 = Driver(name='u2').save()
    o1 = Car(name='o1').save()
    o2 = Car(name='o2').save()

    # test adding a relationship creates the inverse
    u1.proxy.cars.set([o1, o2])

    o1.proxy.drivers.fill()
    o2.proxy.drivers.fill()

    assert type(o1.drivers) == list
    assert type(o2.drivers) == list

    assert len(o1.drivers) == 1
    assert len(o2.drivers) == 1

    assert o1.drivers[0].name == 'u1'
    assert o2.drivers[0].name == 'u1'

    u2.proxy.cars.set([o2])

    o1.proxy.drivers.fill()
    o2.proxy.drivers.fill()

    assert type(o1.drivers) == list
    assert type(o2.drivers) == list

    assert len(o1.drivers) == 1
    assert len(o2.drivers) == 2

    o2.drivers.sort(key=lambda x:x.name)

    assert o1.drivers[0].name == 'u1'
    assert o2.drivers[0].name == 'u1'
    assert o2.drivers[1].name == 'u2'

    # test deleting an object deletes the relationship in the related

    u1.delete()

    o1.proxy.drivers.fill()
    o2.proxy.drivers.fill()

    assert type(o1.drivers) == list
    assert type(o2.drivers) == list

    assert len(o1.drivers) == 0
    assert len(o2.drivers) == 1

def test_querying_related(nrm):
    o1 = Car(name='o1').save()
    u1 = Driver(name='u1').save()
    u2 = Driver(name='u2').save()
    u1.proxy.cars.set([o1])

    assert u1 in o1.proxy.drivers
    assert u2 not in o1.proxy.drivers

def test_can_filter_related(nrm):
    p = Person(name='Juan').save()

    pets = [
        Pet(name='bc').save(), # 0
        Pet(name='bd').save(), # 1
        Pet(name='cd').save(), # 2
    ]

    p.proxy.pets.set(pets)

    assert isinstance(p.proxy.pets.q().filter(name__startswith='pa'), Iterable)

    res = list(map(
        lambda x:x.id,
        p.proxy.pets.q().filter(name__startswith='b', name__endswith='d')
    ))

    assert res == [pets[1].id]

    res = list(map(
        lambda x:x.id,
        p.proxy.pets.q().filter(name__startswith='b').filter(name__endswith='d')
    ))

    assert res == [pets[1].id]

def test_foreign_key(nrm):
    owner = Person(name='John').save()
    pet = Pet(name='doggo').save()

    pet.proxy.owner.set(owner)
    owner.proxy.pets.fill()

    assert pet.owner is not None
    assert pet.owner.id == owner.id

    assert type(owner.pets) == list
    assert len(owner.pets) == 1
    assert owner.pets[0].id == pet.id

    pet.delete()

    pet.proxy.owner.fill()
    owner.proxy.pets.fill()

    assert type(owner.pets) == list
    assert len(owner.pets) == 0

def test_foreign_key_inverse(nrm):
    pet = Pet(name='doggo').save()
    owner = Person(name='John').save()
    owner.proxy.pets.set([pet])

    pet.proxy.owner.fill()
    owner.proxy.pets.fill()

    assert pet.owner is not None
    assert pet.owner.id == owner.id

    assert type(owner.pets) == list
    assert len(owner.pets) == 1
    assert owner.pets[0].id == pet.id

def test_delete_relation(nrm):
    c1 = Car().save()
    c2 = Car().save()

    d1 = Driver().save()

    d1.proxy.cars.set([c1, c2])

    assert c1 in d1.proxy.cars
    assert c2 in d1.proxy.cars
    assert d1 in c1.proxy.drivers
    assert d1 in c2.proxy.drivers

    d1.proxy.cars.remove(c1)

    assert c1 not in d1.proxy.cars
    assert c2 in d1.proxy.cars
    assert d1 not in c1.proxy.drivers
    assert d1 in c2.proxy.drivers

def test_get_relation(nrm):
    c1 = Car().save()
    c2 = Car().save()

    d1 = Driver().save()

    d1.proxy.cars.set([c1, c2])

    cars = d1.proxy.cars.get()

    orig = sorted([c1, c2], key=lambda c:c.id)
    cars = sorted(cars, key=lambda c:c.id)

    assert orig == cars

def test_get_foreignid_relation(nrm):
    pet = Pet().save()
    owner = Person().save()
    owner.proxy.pets.add(pet)

    assert pet.proxy.owner.get().id == owner.id

    owner.proxy.pets.remove(pet)

    assert pet.proxy.owner.get() is None

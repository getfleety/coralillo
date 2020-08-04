from collections.abc import Iterable
from .models import Pet, Person, Driver, Car


def test_relation(nrm):
    org = Car(
        name = 'Testing Inc',
    ).save()

    user = Driver(
        name = 'Sam',
    ).save()

    user.cars.set([org])

    assert user.cars.count() == 1

    assert user.cars.all()[0].id == org.id
    assert nrm.redis.sismember('driver:{}:srel_cars'.format(user.id), org.id)

    same = Driver.get(user.id)

    assert same.cars.all()[0].id == org.id
    assert same.to_json(include=['cars'])['cars'][0]['name'] == 'Testing Inc'


def test_delete_cascade(nrm):
    doggo = Pet(name='doggo').save()
    catto = Pet(name='catto').save()

    owner = Person(
        name = 'John',
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

    owner = Person(
        name = 'John',
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

    assert type(o1.drivers.all()) == list
    assert type(o2.drivers.all()) == list

    assert len(o1.drivers) == 1
    assert len(o2.drivers) == 1

    assert o1.drivers[0].name == 'u1'
    assert o2.drivers[0].name == 'u1'

    u2.cars.set([o2])

    assert type(o1.drivers.all()) == list
    assert type(o2.drivers.all()) == list

    assert len(o1.drivers) == 1
    assert len(o2.drivers) == 2

    o2.drivers.sort(key=lambda x:x.name)

    assert o1.drivers[0].name == 'u1'
    assert o2.drivers[0].name == 'u1'
    assert o2.drivers[1].name == 'u2'

    # test deleting an object deletes the relationship in the related

    u1.delete()

    assert type(o1.drivers.all()) == list
    assert type(o2.drivers.all()) == list

    assert len(o1.drivers) == 0
    assert len(o2.drivers) == 1


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
        Pet(name='bc').save(), # 0
        Pet(name='bd').save(), # 1
        Pet(name='cd').save(), # 2
    ]

    p.pets.set(pets)

    assert isinstance(p.pets.q().filter(name__startswith='pa'), Iterable)

    res = list(map(
        lambda x:x.id,
        p.pets.q().filter(name__startswith='b', name__endswith='d')
    ))

    assert res == [pets[1].id]

    res = list(map(
        lambda x:x.id,
        p.pets.q().filter(name__startswith='b').filter(name__endswith='d')
    ))

    assert res == [pets[1].id]


def test_foreign_key(nrm):
    owner = Person(name='John').save()
    pet = Pet(name='doggo').save()

    pet.owner.set(owner)

    assert pet.owner is not None
    assert pet.owner.id == owner.id

    assert type(owner.pets) == list
    assert len(owner.pets) == 1
    assert owner.pets[0].id == pet.id

    pet.delete()

    assert type(owner.pets) == list
    assert len(owner.pets) == 0


def test_foreign_key_inverse(nrm):
    pet = Pet(name='doggo').save()
    owner = Person(name='John').save()
    owner.pets.set([pet])

    assert pet.owner is not None
    assert pet.owner.id == owner.id

    assert type(owner.pets) == list
    assert len(owner.pets) == 1
    assert owner.pets[0].id == pet.id


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


def test_get_relation(nrm):
    c1 = Car().save()
    c2 = Car().save()

    d1 = Driver().save()

    d1.cars.set([c1, c2])

    cars = d1.cars.get()

    orig = sorted([c1, c2], key=lambda c:c.id)
    cars = sorted(cars, key=lambda c:c.id)

    assert orig == cars


def test_get_foreignid_relation(nrm):
    pet = Pet().save()
    owner = Person().save()
    owner.pets.add(pet)

    assert pet.owner.get().id == owner.id

    owner.pets.remove(pet)

    assert pet.owner.get() is None

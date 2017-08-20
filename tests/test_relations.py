from norm import create_engine
from models import Pet, Person, Driver, Car
import unittest

nrm = create_engine()


class RelationTestCase(unittest.TestCase):

    def setUp(self):
        nrm.lua.drop(args=['*'])

    def test_relation(self):
        org = Car(
            name      = 'Testing Inc',
        ).save(nrm.redis)

        user = Driver(
            name      = 'Sam',
        ).save(nrm.redis)
        user.proxy.cars.set([org], nrm.redis)

        self.assertEqual(user.cars[0].id, org.id)
        self.assertTrue(nrm.redis.sismember('driver:{}:srel_cars'.format(user.id), org.id))

        same = Driver.get(user.id, nrm.redis)
        same.proxy.cars.fill(nrm.redis)

        self.assertEqual(same.cars[0].id, org.id)
        self.assertEqual(same.to_json()['relations']['cars'][0]['attributes']['name'], 'Testing Inc')

    def test_delete_with_related(self):
        doggo = Pet(name='doggo').save(nrm.redis)
        catto = Pet(name='catto').save(nrm.redis)

        owner = Person(
            name = 'John',
        ).save(nrm.redis)
        owner.proxy.pets.set([doggo, catto], nrm.redis)

        self.assertTrue(owner.proxy.pets.has(doggo, nrm.redis))
        self.assertTrue(owner.proxy.pets.has(catto, nrm.redis))

        owner.delete(nrm.redis)

        self.assertIsNone(Pet.get(doggo.id, nrm.redis))
        self.assertIsNone(Pet.get(catto.id, nrm.redis))

    def test_many_to_many_relationship(self):
        u1 = Driver(name='u1').save(nrm.redis)
        u2 = Driver(name='u2').save(nrm.redis)
        o1 = Car(name='o1').save(nrm.redis)
        o2 = Car(name='o2').save(nrm.redis)

        # test adding a relationship creates the inverse
        u1.proxy.cars.set([o1, o2], nrm.redis)

        o1.proxy.drivers.fill(nrm.redis)
        o2.proxy.drivers.fill(nrm.redis)

        self.assertTrue(type(o1.drivers) == list)
        self.assertTrue(type(o2.drivers) == list)

        self.assertEqual(len(o1.drivers), 1)
        self.assertEqual(len(o2.drivers), 1)

        self.assertEqual(o1.drivers[0].name, 'u1')
        self.assertEqual(o2.drivers[0].name, 'u1')

        u2.proxy.cars.set([o2], nrm.redis)

        o1.proxy.drivers.fill(nrm.redis)
        o2.proxy.drivers.fill(nrm.redis)

        self.assertTrue(type(o1.drivers) == list)
        self.assertTrue(type(o2.drivers) == list)

        self.assertEqual(len(o1.drivers), 1)
        self.assertEqual(len(o2.drivers), 2)

        o2.drivers.sort(key=lambda x:x.name)

        self.assertEqual(o1.drivers[0].name, 'u1')
        self.assertEqual(o2.drivers[0].name, 'u1')
        self.assertEqual(o2.drivers[1].name, 'u2')

        # test deleting an object deletes the relationship in the related

        u1.delete(nrm.redis)

        o1.proxy.drivers.fill(nrm.redis)
        o2.proxy.drivers.fill(nrm.redis)

        self.assertTrue(type(o1.drivers) == list)
        self.assertTrue(type(o2.drivers) == list)

        self.assertEqual(len(o1.drivers), 0)
        self.assertEqual(len(o2.drivers), 1)

    def test_querying_related(self):
        o1 = Car(name='o1').save(nrm.redis)
        u1 = Driver(name='u1').save(nrm.redis)
        u2 = Driver(name='u2').save(nrm.redis)
        u1.proxy.cars.set([o1], nrm.redis)

        self.assertTrue(o1.proxy.drivers.has(u1, nrm.redis))
        self.assertFalse(o1.proxy.drivers.has(u2, nrm.redis))

    def test_foreign_key(self):
        owner = Person(name='John').save(nrm.redis)
        pet = Pet(name='doggo').save(nrm.redis)

        pet.proxy.owner.set(owner, nrm.redis)
        owner.proxy.pets.fill(nrm.redis)

        self.assertIsNotNone(pet.owner)
        self.assertEqual(pet.owner.id, owner.id)

        self.assertTrue(type(owner.pets) == list)
        self.assertEqual(len(owner.pets), 1)
        self.assertEqual(owner.pets[0].id, pet.id)

        pet.delete(nrm.redis)

        pet.proxy.owner.fill(nrm.redis)
        owner.proxy.pets.fill(nrm.redis)

        self.assertTrue(type(owner.pets) == list)
        self.assertEqual(len(owner.pets), 0)

    def test_foreign_key_inverse(self):
        pet = Pet(name='doggo').save(nrm.redis)
        owner = Person(name='John').save(nrm.redis)
        owner.proxy.pets.set([pet], nrm.redis)

        pet.proxy.owner.fill(nrm.redis)
        owner.proxy.pets.fill(nrm.redis)

        self.assertIsNotNone(pet.owner)
        self.assertEqual(pet.owner.id, owner.id)

        self.assertTrue(type(owner.pets) == list)
        self.assertEqual(len(owner.pets), 1)
        self.assertEqual(owner.pets[0].id, pet.id)


if __name__ == '__main__':
    unittest.main()

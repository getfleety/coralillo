from .models import Pet, Person, Driver, Car, nrm
import unittest


class RelationTestCase(unittest.TestCase):

    def setUp(self):
        nrm.lua.drop(args=['*'])

    def test_relation(self):
        org = Car(
            name      = 'Testing Inc',
        ).save()

        user = Driver(
            name      = 'Sam',
        ).save()
        user.proxy.cars.set([org])

        self.assertEqual(user.proxy.cars.count(), 1)

        self.assertEqual(user.cars[0].id, org.id)
        self.assertTrue(nrm.redis.sismember('driver:{}:srel_cars'.format(user.id), org.id))

        same = Driver.get(user.id)
        same.proxy.cars.fill()

        self.assertEqual(same.cars[0].id, org.id)
        self.assertEqual(same.to_json(embed=['cars'])['cars'][0]['name'], 'Testing Inc')

    def test_delete_with_related(self):
        doggo = Pet(name='doggo').save()
        catto = Pet(name='catto').save()

        owner = Person(
            name = 'John',
        ).save()
        owner.proxy.pets.set([doggo, catto])

        self.assertTrue(doggo in owner.proxy.pets)
        self.assertTrue(catto in owner.proxy.pets)

        owner.delete()

        self.assertIsNone(Pet.get(doggo.id))
        self.assertIsNone(Pet.get(catto.id))

    def test_many_to_many_relationship(self):
        u1 = Driver(name='u1').save()
        u2 = Driver(name='u2').save()
        o1 = Car(name='o1').save()
        o2 = Car(name='o2').save()

        # test adding a relationship creates the inverse
        u1.proxy.cars.set([o1, o2])

        o1.proxy.drivers.fill()
        o2.proxy.drivers.fill()

        self.assertTrue(type(o1.drivers) == list)
        self.assertTrue(type(o2.drivers) == list)

        self.assertEqual(len(o1.drivers), 1)
        self.assertEqual(len(o2.drivers), 1)

        self.assertEqual(o1.drivers[0].name, 'u1')
        self.assertEqual(o2.drivers[0].name, 'u1')

        u2.proxy.cars.set([o2])

        o1.proxy.drivers.fill()
        o2.proxy.drivers.fill()

        self.assertTrue(type(o1.drivers) == list)
        self.assertTrue(type(o2.drivers) == list)

        self.assertEqual(len(o1.drivers), 1)
        self.assertEqual(len(o2.drivers), 2)

        o2.drivers.sort(key=lambda x:x.name)

        self.assertEqual(o1.drivers[0].name, 'u1')
        self.assertEqual(o2.drivers[0].name, 'u1')
        self.assertEqual(o2.drivers[1].name, 'u2')

        # test deleting an object deletes the relationship in the related

        u1.delete()

        o1.proxy.drivers.fill()
        o2.proxy.drivers.fill()

        self.assertTrue(type(o1.drivers) == list)
        self.assertTrue(type(o2.drivers) == list)

        self.assertEqual(len(o1.drivers), 0)
        self.assertEqual(len(o2.drivers), 1)

    def test_querying_related(self):
        o1 = Car(name='o1').save()
        u1 = Driver(name='u1').save()
        u2 = Driver(name='u2').save()
        u1.proxy.cars.set([o1])

        self.assertTrue(u1 in o1.proxy.drivers)
        self.assertFalse(u2 in o1.proxy.drivers)

    def test_foreign_key(self):
        owner = Person(name='John').save()
        pet = Pet(name='doggo').save()

        pet.proxy.owner.set(owner)
        owner.proxy.pets.fill()

        self.assertIsNotNone(pet.owner)
        self.assertEqual(pet.owner.id, owner.id)

        self.assertTrue(type(owner.pets) == list)
        self.assertEqual(len(owner.pets), 1)
        self.assertEqual(owner.pets[0].id, pet.id)

        pet.delete()

        pet.proxy.owner.fill()
        owner.proxy.pets.fill()

        self.assertTrue(type(owner.pets) == list)
        self.assertEqual(len(owner.pets), 0)

    def test_foreign_key_inverse(self):
        pet = Pet(name='doggo').save()
        owner = Person(name='John').save()
        owner.proxy.pets.set([pet])

        pet.proxy.owner.fill()
        owner.proxy.pets.fill()

        self.assertIsNotNone(pet.owner)
        self.assertEqual(pet.owner.id, owner.id)

        self.assertTrue(type(owner.pets) == list)
        self.assertEqual(len(owner.pets), 1)
        self.assertEqual(owner.pets[0].id, pet.id)

    def test_delete_relation(self):
        c1 = Car().save()
        c2 = Car().save()

        d1 = Driver().save()

        d1.proxy.cars.set([c1, c2])

        self.assertTrue(c1 in d1.proxy.cars)
        self.assertTrue(c2 in d1.proxy.cars)
        self.assertTrue(d1 in c1.proxy.drivers)
        self.assertTrue(d1 in c2.proxy.drivers)

        d1.proxy.cars.remove(c1)

        self.assertFalse(c1 in d1.proxy.cars)
        self.assertTrue(c2 in d1.proxy.cars)
        self.assertFalse(d1 in c1.proxy.drivers)
        self.assertTrue(d1 in c2.proxy.drivers)

    def test_get_relation(self):
        c1 = Car().save()
        c2 = Car().save()

        d1 = Driver().save()

        d1.proxy.cars.set([c1, c2])

        cars = d1.proxy.cars.get()

        orig = sorted([c1, c2], key=lambda c:c.id)
        cars = sorted(cars, key=lambda c:c.id)

        self.assertListEqual(orig, cars)

    def test_get_foreignid_relation(self):
        pet = Pet().save()
        owner = Person().save()
        owner.proxy.pets.add(pet)

        self.assertEqual(pet.proxy.owner.get().id, owner.id)

        owner.proxy.pets.remove(pet)

        self.assertIsNone(pet.proxy.owner.get())


if __name__ == '__main__':
    unittest.main()

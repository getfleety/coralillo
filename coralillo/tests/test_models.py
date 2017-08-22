from coralillo import datamodel, Engine, Model, BoundedModel, fields
from coralillo.datamodel import debyte_string
import unittest

nrm = Engine()


class Person(Model):
    name = fields.Text()

    class Meta:
        engine = nrm


class Ship(Model):
    name = fields.Text()
    code = fields.Text(index=True)

    class Meta:
        engine = nrm


class Pet(BoundedModel):
    name = fields.Text()

    @classmethod
    def prefix(cls):
        return 'testing'

    class Meta:
        engine = nrm


class ModelTestCase(unittest.TestCase):

    def setUp(self):
        nrm.lua.drop(args=['*'])

    def test_create_user(self):
        user = Person(
            name      = 'John',
        ).save()

        self.assertEqual(user.name, 'John')

        self.assertTrue(nrm.redis.sismember('person:members', user.id))
        self.assertEqual(nrm.redis.hget('person:{}'.format(user.id), 'name'), b'John')

    def test_retrieve_user_by_id(self):
        carla = Person( name = 'Carla',).save()
        roberta = Person( name = 'Roberta',).save()

        read_user = Person.get(carla.id)

        self.assertEqual(read_user.name, carla.name)

    def test_retrieve_by_index(self):
        titan = Ship(name='te trece', code = 'T13',).save()
        atlan = Ship(name='te catorce', code = 'T14',).save()

        found_ship = Ship.get_by('code', 'T13')

        self.assertIsNotNone(found_ship)
        self.assertTrue(titan == found_ship)

    def test_update_keep_index(self):
        ship = Ship(name='the ship', code='TS').save()

        ship.update(name='updated name')

        self.assertEqual(ship.code, 'TS')
        self.assertEqual(ship.name, 'updated name')

        self.assertEqual(debyte_string(nrm.redis.hget('ship:index_code', 'TS')), ship.id)

    def test_update_changes_index(self):
        ship = Ship(code='THECODE').save()

        ship.update(code='NEWCODE')

        self.assertEqual(ship.code, 'NEWCODE')

        self.assertEqual(debyte_string(nrm.redis.hget('ship:index_code', 'NEWCODE')), ship.id)
        self.assertIsNone(nrm.redis.hget('ship:index_code', 'THECODE'))

    def test_get(self):
        org = Person(name='Juan').save()
        got = Person.get(org.id)

        self.assertTrue(org == got)

    def test_get_all(self):
        p1 = Person(name='Juan').save()
        p2 = Person(name='Pepe').save()

        allitems = Person.get_all()

        allitems.sort(key=lambda x: x.name)

        item1 = allitems[0]
        item2 = allitems[1]

        self.assertEqual(item1, p1)
        self.assertEqual(item2, p2)

    def test_bounded_model(self):
        dev = Pet(
            name = 'foo',
        ).save()

        self.assertFalse(nrm.redis.exists('pet:'+dev.id))
        self.assertTrue(nrm.redis.exists('testing:pet:'+dev.id))
        self.assertEqual(nrm.redis.hget('testing:pet:'+dev.id, 'name'), b'foo')
        self.assertTrue(nrm.redis.sismember('testing:pet:members', dev.id))

    def test_delete(self):
        dev = Pet(
            code = 'foo',
        ).save()

        self.assertIsNotNone(Pet.get(dev.id))

        dev.delete()

        self.assertIsNone(Pet.get(dev.id))
        self.assertFalse(nrm.redis.sismember('testing:pet:members', dev.id))

    def test_delete_index(self):
        ship = Ship(code='A12').save()

        self.assertEqual(debyte_string(nrm.redis.hget('ship:index_code', 'A12')), ship.id)

        ship.delete()

        self.assertFalse(nrm.redis.hexists('ship:index_code', 'A12'))


if __name__ == '__main__':
    unittest.main()

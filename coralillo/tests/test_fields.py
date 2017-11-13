from coralillo import Engine, Model, datamodel
from coralillo.fields import *
from coralillo.hashing import check_password
from datetime import datetime
import unittest
import time
import os

nrm = Engine()

os.environ['TZ'] = 'UTC'
time.tzset()


class BaseModel(Model):
    class Meta:
        engine = nrm


class User(BaseModel):
    password = Hash()


class Car(BaseModel):
    last_position = Location()


class Subscription(BaseModel):
    key_name = TreeIndex()


class FieldTestCase(unittest.TestCase):

    def setUp(self):
        nrm.lua.drop(args=['*'])
        self.pwd = 'bcrypt$$2b$12$gWQweaiLPJr2OHSPOshyQe3zmnSAPGv2pA.PwOIuxZ3ylvLMN7h6C'

    def test_field_text(self):
        field = Text(name='field', default='pollo')

        self.assertEqual(field.recover({'field': 'foo'}, 'field'), 'foo')
        self.assertEqual(field.prepare('foo'), 'foo')
        self.assertEqual(field.validate(None, 'field'), 'pollo')
        self.assertEqual(field.recover({'field': ''}, 'field'), '')
        self.assertEqual(field.recover({'field': None}, 'field'), None)
        self.assertEqual(field.recover({'field': 'None'}, 'field'), None)

    def test_field_text_validate(self):
        field = Text(name='field')

        with self.assertRaises(MissingFieldError):
            field.validate('', None)

    def test_field_hash(self):
        field = Hash(name='field')

        self.assertEqual(field.recover({'field': 'foo'}, 'field'), 'foo')
        self.assertNotEqual(field.validate('foo', 'field'), 'foo')
        self.assertEqual(field.recover({'field': None}, 'field'), None)
        self.assertEqual(field.recover({'field': 'None'}, 'field'), None)

    def test_field_bool(self):
        field = Bool(name='field')

        self.assertEqual(field.recover({'field': 'True'}, 'field'), True)
        self.assertEqual(field.recover({'field': 'False'}, 'field'), False)
        self.assertEqual(field.prepare(True), 'True')
        self.assertEqual(field.prepare(False), 'False')
        self.assertEqual(field.recover({'field': None}, 'field'), None)
        self.assertEqual(field.recover({'field': 'None'}, 'field'), None)

        self.assertEqual(field.validate('true', 'field'), True)
        self.assertEqual(field.validate('false', 'field'), False)
        self.assertEqual(field.validate('1', 'field'), True)
        self.assertEqual(field.validate('0', 'field'), False)
        self.assertEqual(field.validate('', 'field'), False)

    def test_field_int(self):
        field = Integer(name='field')

        self.assertEqual(field.recover({'field': '35'}, 'field'), 35)
        self.assertEqual(field.recover({'field': '0'}, 'field'), 0)
        self.assertEqual(field.recover({'field': ''}, 'field'), None)
        self.assertEqual(field.recover({'field': None}, 'field'), None)
        self.assertEqual(field.recover({'field': 'None'}, 'field'), None)

        self.assertEqual(field.prepare(35), '35')
        self.assertEqual(field.prepare(0), '0')

        self.assertEqual(field.validate(0, 'field'), 0)
        self.assertEqual(field.validate('0', 'field'), 0)

        with self.assertRaises(MissingFieldError):
            field.validate('', 'field')

        with self.assertRaises(InvalidFieldError):
            field.validate('pollo', 'field')

    def test_field_int_no_required(self):
        field = Integer(name='field', required=False)

        self.assertEqual(field.validate(None, 'field'), None)
        self.assertEqual(field.validate('', 'field'), None)

    def test_field_float(self):
        field = Float(name='field')

        self.assertEqual(field.recover({'field': '3.14'}, 'field'), 3.14)
        self.assertEqual(field.recover({'field': '0'}, 'field'), 0.0)
        self.assertEqual(field.recover({'field': ''}, 'field'), None)
        self.assertEqual(field.recover({'field': None}, 'field'), None)
        self.assertEqual(field.recover({'field': 'None'}, 'field'), None)

        self.assertEqual(field.prepare(3.14), '3.14')
        self.assertEqual(field.prepare(0.0), '0.0')

        self.assertEqual(field.validate(0, 'field'), 0)
        self.assertEqual(field.validate('0', 'field'), 0)

    def test_field_date(self):
        field = Datetime(name='field')

        self.assertEqual(field.recover({'field': '1499794899'}, 'field'), datetime(2017, 7, 11, 17, 41, 39))
        self.assertEqual(field.recover({'field': ''}, 'field'), None)
        self.assertEqual(field.recover({'field': None}, 'field'), None)
        self.assertEqual(field.recover({'field': 'None'}, 'field'), None)
        self.assertEqual(field.prepare(datetime(2017, 7, 11, 17, 41, 39)), '1499794899')

    def test_field_location(self):
        class MyModel(Model):
            field = Location()

            class Meta:
                engine = nrm

        obj = MyModel(field = datamodel.Location(-103.3590, 20.7240)).save()

        self.assertEqual(nrm.redis.type('my_model:geo_field'), b'zset')
        self.assertEqual(MyModel.get(obj.id).field, datamodel.Location(-103.3590, 20.7240))

    def test_field_location_validate(self):
        class MyModel(Model):
            field = Location()

            class Meta:
                engine = nrm

        item = MyModel.validate(field='-100,20').save()
        self.assertEqual(item.field, datamodel.Location(-100, 20))

        item_rec = MyModel.get(item.id)
        self.assertEqual(item_rec.field, datamodel.Location(-100, 20))

    def test_field_location_none(self):
        class MyModel(Model):
            field = Location(required=False)

            class Meta:
                engine = nrm

        item = MyModel.validate().save()

        item_rec = MyModel.get(item.id)

        self.assertIsNone(item_rec.field)

    def test_password_check(self):
        user = User(
            password  = self.pwd,
        ).save()

        self.assertTrue(check_password('123456', user.password))
        self.assertFalse(user.password == '123456')

    def test_empty_field_dict(self):
        class Dummy(Model):
            dynamic = Dict()

            class Meta:
                engine = nrm

        a = Dummy().save()
        loaded_a = Dummy.get(a.id)

        self.assertDictEqual(loaded_a.dynamic, {})

    def test_field_dict(self):
        class Dummy(Model):
            name           = Text()
            dynamic        = Dict()

            class Meta:
                engine = nrm

        # Create and save models with a dict field
        a = Dummy(
            name = 'dummy',
            dynamic = {
                '1': 'one',
            },
        ).save()

        b = Dummy(
            name = 'dummy',
            dynamic = {
                '2': 'two',
            },
        ).save()

        c = Dummy(
            name = 'dummy',
            dynamic = {
                '1': 'one',
                '2': 'two',
            },
        ).save()

        # override dict
        a.dynamic = {
            '3': 'thre',
        }

        a.save()

        loaded_a = Dummy.get(a.id)
        loaded_b = Dummy.get(b.id)
        loaded_c = Dummy.get(c.id)

        self.assertDictEqual(a.dynamic, loaded_a.dynamic)
        self.assertDictEqual(b.dynamic, loaded_b.dynamic)
        self.assertDictEqual(c.dynamic, loaded_c.dynamic)

    def test_field_position_delete(self):
        c1 = Car(last_position=datamodel.Location(-90, 21)).save()
        c2 = Car(last_position=datamodel.Location(-90, 22)).save()

        self.assertEqual(Car.get(c1.id).last_position, datamodel.Location(-90, 21))
        self.assertEqual(Car.get(c2.id).last_position, datamodel.Location(-90, 22))

        c1.delete()

        self.assertIsNone(Car.get(c1.id))

        self.assertEqual(Car.get(c2.id).last_position, datamodel.Location(-90, 22))

    def test_tree_index(self):
        s4 = Subscription(key_name='a:b:c:d').save()
        s1 = Subscription(key_name='a:b:c').save()
        s2 = Subscription(key_name='a:b').save()
        s3 = Subscription(key_name='a').save()

        self.assertListEqual(Subscription.tree_match('key_name', 'a:b:c'), [s1, s2, s3])

        s3.delete()
        self.assertListEqual(Subscription.tree_match('key_name', 'a:b:c'), [s1, s2])

        s2.delete()
        self.assertListEqual(Subscription.tree_match('key_name', 'a:b:c'), [s1])

        s1.delete()
        self.assertListEqual(Subscription.tree_match('key_name', 'a:b:c'), [])


if __name__ == '__main__':
    unittest.main()

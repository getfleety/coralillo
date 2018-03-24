from coralillo import Engine, Model, fields
from coralillo.errors import UnboundModelError
from random import choice
import unittest


class EngineTestCase(unittest.TestCase):

    def test_create_engine_with_url(self):
        url = 'redis://localhost:6379/0'

    def test_create_engine(self):
        eng1 = Engine(db=11)
        eng2 = Engine(db=12)

        class Dog(Model):
            name = fields.Text()

            class Meta:
                engine = eng1

        class Cat(Model):
            name = fields.Text()

            class Meta:
                engine = eng2

        doggo = Dog(name='doggo').save()
        catto = Cat(name='catto').save()

        self.assertTrue(eng1.redis.exists('dog:{}:obj'.format(doggo.id)))
        self.assertFalse(eng1.redis.exists('cat:{}:obj'.format(catto.id)))

        self.assertTrue(eng2.redis.exists('cat:{}:obj'.format(catto.id)))
        self.assertFalse(eng2.redis.exists('dog:{}:obj'.format(doggo.id)))

    def test_set_engine_delayed(self):
        class Foo(Model):
            name = fields.Text()

        with self.assertRaises(UnboundModelError):
            Foo.get_engine()

        eng = Engine()

        Foo.set_engine(eng)

        self.assertIsNone(Foo.get('de')) # Only possible if bound to engine

    def test_unbound_models(self):
        class Dog(Model):
            name = fields.Text()

        with self.assertRaises(UnboundModelError):
            Dog(mame='doggo').save()

    def test_register_lua_script(self):
        eng = Engine(db=0)

        eng.lua.register('my_script', 'return ARGV[1]')

        self.assertIsNotNone(eng.lua.my_script)
        self.assertEqual(eng.lua.my_script(args=[4]), b'4')

    def test_can_replace_id_function(self):
        def simple_ids():
            return ''.join(choice('123456789abcdef') for c in range(11))

        simple_eng = Engine(id_function=simple_ids)
        uuid_eng = Engine()

        class SimpleDog(Model):
            name = fields.Text()

            class Meta:
                engine = simple_eng

        class UuidDog(Model):
            name = fields.Text()

            class Meta:
                engine = uuid_eng

        simple_doggo = SimpleDog(name='doggo').save()
        self.assertEqual(len(simple_doggo.id), 11)

        uuid_doggo = UuidDog(name='doggo').save()
        self.assertEqual(len(uuid_doggo.id), 32)


if __name__ == '__main__':
    unittest.main()

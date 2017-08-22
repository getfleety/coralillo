from coralillo import Engine, Model, fields
from coralillo.errors import UnboundModelError
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

        self.assertTrue(eng1.redis.exists('dog:{}'.format(doggo.id)))
        self.assertFalse(eng1.redis.exists('cat:{}'.format(catto.id)))

        self.assertTrue(eng2.redis.exists('cat:{}'.format(catto.id)))
        self.assertFalse(eng2.redis.exists('dog:{}'.format(doggo.id)))

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


if __name__ == '__main__':
    unittest.main()

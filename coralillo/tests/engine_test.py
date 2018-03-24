from coralillo import Engine, Model, fields
from coralillo.errors import UnboundModelError
from random import choice
import pytest


def test_create_engine():
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

    assert eng1.redis.exists('dog:{}:obj'.format(doggo.id))
    assert not eng1.redis.exists('cat:{}:obj'.format(catto.id))

    assert eng2.redis.exists('cat:{}:obj'.format(catto.id))
    assert not eng2.redis.exists('dog:{}:obj'.format(doggo.id))

def test_set_engine_delayed():
    class Foo(Model):
        name = fields.Text()

    with pytest.raises(UnboundModelError):
        Foo.get_engine()

    eng = Engine()

    Foo.set_engine(eng)

    assert Foo.get('de') is None

def test_unbound_models():
    class Dog(Model):
        name = fields.Text()

    with pytest.raises(UnboundModelError):
        Dog(mame='doggo').save()

def test_register_lua_script():
    eng = Engine(db=0)

    eng.lua.register('my_script', 'return ARGV[1]')

    assert eng.lua.my_script is not None
    assert eng.lua.my_script(args=[4]) == b'4'

def test_can_replace_id_function():
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
    assert len(simple_doggo.id) == 11

    uuid_doggo = UuidDog(name='doggo').save()
    assert len(uuid_doggo.id) == 32

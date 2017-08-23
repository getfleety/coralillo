Multi-tenancy
=============

It is often useful to have objects of the same class stored within different namespaces, for example when running an application that serves different clients and you don't want them to be in the same place.

For this case Coralillo has a Model subclass called BoundedModel that lets you specify a prefix for your models:

.. testsetup::

    from coralillo import Engine

    eng = Engine()
    eng.lua.drop(args=['*'])

.. testcode::

    from coralillo import Engine, BoundedModel, fields

    eng = Engine()

    current_namespace = 'coral'

    class User(BoundedModel):
        name = fields.Text()

        @classmethod
        def prefix(cls):
            # here you may have your own way of determining the __bound__
            # depending on the context. We will just return a variable's
            # value
            return current_namespace

        class Meta:
            engine = eng

    # models are saved in the namespace given by the context
    juan = User(name='Juan').save()
    assert eng.redis.exists('coral:user:members')

    # changing the context changes how models are found
    current_namespace = 'nauyaca'
    assert User.get(juan.id) is None

    pepe = User(name='Pepe').save()
    assert eng.redis.exists('nauyaca:user:members')

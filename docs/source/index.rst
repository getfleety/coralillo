.. Coralillo documentation master file, created by
   sphinx-quickstart on Tue Aug  1 10:58:55 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Coralillo
=========

Coralillo is a tool intended to provide a convenient API over the Redis data structure store in a similar way that traditional ORMs do.

Basic Usage
-----------

::

    from coralillo import Model, fields

    # Declare your models
    class User(Model):
        name      = fields.Text()
        last_name = fields.Text()
        email     = fields.Text(
            index=True,
            regex='^[\w.%+-]+@[\w.-]+\.[a-zA-Z]{2,}$',
        )

    # Persist objects to database
    john = User(
        name='John',
        last_name='Doe',
        email='john@example.com',
    ).save()

    # Query by index
    mary = User.get_by('email', 'mary@example.com')

    # Retrieve all objects
    users = User.get_all()

Relationships
-------------

::

    from coralillo import Model, fields

    class Group(Model):
        name  = fields.Text()
        # Declare your relationships and the name of the relationship
        # in the related model
        users = fields.SetRelation('models.User', inverse='group')

    class User(Model):
        name  = fields.Text()
        # you can use either the class or a module string to
        # declare relationships
        group = fields.ForeignIdRelation(Group, inverse='users')

    developers = Group(name='developers').save()

    john = User(
        name='John Doe',
        # assign objects to the relationships
        group=developers,
    # Don't forget to tell the orm to save the relations
    ).save(save_relations=True)

    assert john.group.id == developers.id

    # Relationships are not loaded by default
    developers.proxy.users.load()

    assert developers.users[0].id == john.id

Contents
--------

.. toctree::
   :maxdepth: 2

   fields


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

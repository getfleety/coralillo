Coralillo
=========

Coralillo is an ORM (Object-Redis Mapping) for pyton. It is named after a little red snake (Coral snake) that you can find in México.

Installation
------------

Install it via ``pip``

``$ pip install coralillo``

It is good idea to manage your dependencies inside a virtualenv.

Basic Usage
-----------

.. testcode::

    from coralillo import Engine, Model, fields

    # Create the engine
    eng = Engine()

    # Declare your models
    class User(Model):
        name      = fields.Text()
        last_name = fields.Text()
        email     = fields.Text(
            index=True,
            regex='^[\w.%+-]+@[\w.-]+\.[a-zA-Z]{2,}$',
        )

        class Meta:
            engine = eng

    # Persist objects to database
    john = User(
        name='John',
        last_name='Doe',
        email='john@example.com',
    ).save()

    # Query by index
    mary = User.get_by('email', 'mary@example.com')

    # Retrieve all objects
    users = User.all()

Learn More
----------

.. toctree::
   :maxdepth: 2

   connection_parameters
   fields
   validation
   flask_integration
   scripting
   multi_tenancy
   atomic_operations
   extending
   design_desitions
   helpers
   api

Indices and tables
------------------

* :ref:`genindex`
* :ref:`search`

Coralillo
=========


.. image:: https://travis-ci.org/getfleety/coralillo.svg?branch=master
   :target: https://travis-ci.org/getfleety/coralillo
   :alt: Build Status


A redis ORM.

Notes
-----

Version 1.0 depends on redis >= 3.0.

Installation
------------

.. code-block:: bash

   $ pip install coralillo

Usage
-----

.. code:: python

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

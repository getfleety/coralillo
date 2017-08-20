Fields
======

Fields let you define your object's properties and transform the values retrieved from the database, we support the following:

* ``fields.Text`` A simple text field
* ``fields.Hash`` A hashed text using bcrypt
* ``fields.Bool`` A true/false value
* ``fields.Integer`` An integer
* ``fields.Float`` A floating point value
* ``fields.Datetime`` A date and time
* ``fields.Location`` A pair of latitude/longitude

Relation fields
---------------

We also provide fields for defining relationships with other models in a ORM-fashion

* ``fields.SetRelation`` Stored as a set of the related ids
* ``fields.SortedSetRelation`` Stored as a sorteed set of the related ids, using a sotring key
* ``fields.ForeignIdRelation`` simply stores the string id of the related object

Indexes
-------

Only Text fields are ready to be indexes

Creating your own fields
------------------------

Simply subclass ``Field`` or ``Relation``.

NORM fields follow an specific workflow to read/write from/to the redis database. Such workflow needs the following methods to be implemented (or inherited) for each field:

* ``__init__`` for field initialization, don't forget to call the parent's constructor
* ``init`` is called to parse a value given in the model's constructor
* ``recover`` is called to parse a value retrieved from database
* ``prepare`` is called to transform values or *prepare* them to be sent to database
* ``to_json`` should return the json-friendly version of the value
* ``validate`` is called when doing ``Model.validate(data)`` or ``obj.update(data)``

Additionally, the following methods are needed for ``Relation`` subclasses:

.. function:: save(value, pipeline[, commit=True])

   persists this relationship to the database

.. function:: relate(obj, pipeline)

   sets the given object as related to the one that owns this field

.. function:: delete(pipeline)

   tells what to do when a model with relationships is deleted

.. function:: key()

   returns a fully qualified redis key to this relationship

.. function:: get_related_ids()

   for subclasses of ``SetRelation``, returns the list of related ids

.. function:: fill()

   is called when you need to know the relationships for a model. Usually via the proxy object.

.. function:: __contains__(obj)

   is for subclasses of ``SetRelation`` and should tell wether or not the given object is in this relation. Usually called via the proxy object.

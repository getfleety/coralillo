Defining models
===============

These are all the fields available right now:

* ``Text`` for strings of any size
* ``Hash`` for passwords
* ``Bool`` for boolean values
* ``Integer`` for ints
* ``Float`` for floating point numbers
* ``Datetime`` for timestamps
* ``Location`` for gps positions (Requires redis-py >= 2.10.6)
* ``Dict`` for key-value pairs

Relationships
-------------

You can also define relationships between models the same way you do in relational databases using the following fields:

* ``ForeignIdRelation`` says that this models is related to only one of the other
* ``SetRelation`` states that this model ows or is related to many of the other
* ``SortedSetRelation`` is a special case of the set relation in which you want the related objects sorteed by the specified key

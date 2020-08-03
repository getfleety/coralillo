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

Testing
-------

Since this project uses pytest is as easy as:

.. code-block:: bash

   $ pytest

Deploy
------

Make a tag with the corresponding release number, then:

.. code-block:: bash

   $ make clean
   $ make release

Coralillo
=========


.. image:: https://travis-ci.org/getfleety/coralillo.svg?branch=master
   :target: https://travis-ci.org/getfleety/coralillo
   :alt: Build Status


A redis ORM. This project is in active development, if you think it is useful contact me so we can talk about its usage, features and future of the project.

Installation
------------

.. code-block:: bash

   $ pip install coralillo

Testing
-------

Runing the test suite:

.. code-block:: bash

   $ python setup.py test

Or you can run individual tests using builtin unittest API:

.. code-block:: bash

   $ python coralillo/tests/test_all.py [-f] [TestCaseClass[.test_function]]

Deploy
------

Make a tag with the corresponding release number, then:

.. code-block:: bash

   $ make clean
   $ make release

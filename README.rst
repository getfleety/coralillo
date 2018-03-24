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

Since this project uses pytest is as easy as:

.. code-block:: bash

   $ pytest

Deploy
------

Make a tag with the corresponding release number, then:

.. code-block:: bash

   $ make clean
   $ make release

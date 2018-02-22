Connection parameters
=====================

By default ``Engine()`` connects to localhost using the default port and database number **0**. If you want to connect to a different host, port or database you can use an URL like in the following example:

.. testcode::

   from coralillo import Engine

   HOST = 'localhost'
   PORT = 6379
   DB = 0

   redis_url = 'redis://{host}:{port}/{db}'.format(
      host = HOST,
      port = PORT,
      db = DB,
   )
   eng = Engine(url=redis_url)

For more information on how to build the URL refer to https://github.com/andymccurdy/redis-py/blob/master/redis/client.py#L462 .

Another option would be to pass the configuration parameters directly like this:

.. testcode::

   from coralillo import Engine

   HOST = 'localhost'
   PORT = 6379
   DB = 0

   eng = Engine(
      host = HOST,
      port = PORT,
      db = DB,
   )

For a full reference on the keyword arguments that you can pass refer to https://github.com/andymccurdy/redis-py/blob/master/redis/client.py#L490 .

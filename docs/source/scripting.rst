Lua scripting
=============

Coralillo uses a few lua scripts to atomically run certain operations. These can be accessed through the engine's ``lua`` object. Here are the available scripts:

.. function:: engine.lua.drop(args=[pattern])

   Deletes all keys matching ``pattern`` from the database. Specially useful in tests.

.. function:: engine.lua.allow(args=[objspec], keys=[allow_key])

   Adds objspec to the permission tree stored at ``allow_key``

Script registering
------------------

You can add your own scripts using Coralillo's lua interface like this:

.. testcode::

    from coralillo import Engine

    eng = Engine()

    script = 'return ARGV[1]'

    eng.lua.register('my_script', script)

    assert eng.lua.my_script(args=['hello']) == b'hello'

.. function:: Lua.register(scriptname, scriptbody)

   Registers script defined by ``scriptbody`` (a string) so it is accessible through the ``lua`` interface of the engine under the name ``scriptname``.

Lua scripting
=============

Coralillo uses a few lua scripts to atomically run certain operations. You can add your own scripts using Coralillo's lua interface like this:

.. testcode::

    from coralillo import Engine

    eng = Engine()

    script = 'return ARGV[1]'

    eng.lua.register('my_script', script)

    assert eng.lua.my_script(args=['hello']) == b'hello'

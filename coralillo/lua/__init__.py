import os

SCRIPT_PATH = os.path.dirname(__file__)

class Lua:

    def __init__(self, redis):
        self.redis = redis
        scripts = filter(lambda s:s.endswith('.lua'), os.listdir(SCRIPT_PATH))

        for scriptname in scripts:
            with open(os.path.join(SCRIPT_PATH, scriptname)) as script:
                setattr(self, scriptname.split('.')[0], redis.register_script(script.read()))

    def register(self, name, contents):
        setattr(self, name, self.redis.register_script(contents))

import os

SCRIPT_PATH = os.path.dirname(__file__)

class Lua:

    def __init__(self, redis):
        self.drop          = redis.register_script(open(os.path.join(SCRIPT_PATH, './drop.lua')).read())
        self.device_motion = redis.register_script(open(os.path.join(SCRIPT_PATH, './device_motion.lua')).read())
        self.text_search   = redis.register_script(open(os.path.join(SCRIPT_PATH, './text_search.lua')).read())
        self.allow         = redis.register_script(open(os.path.join(SCRIPT_PATH, './allow.lua')).read())
        self.is_allowed    = redis.register_script(open(os.path.join(SCRIPT_PATH, './is_allowed.lua')).read())
        self.clear_related_permissions = redis.register_script(open(os.path.join(SCRIPT_PATH, './clear_related_permissions.lua')).read())

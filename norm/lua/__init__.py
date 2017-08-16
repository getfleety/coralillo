from fleety import redis
import os

SCRIPT_PATH = os.path.dirname(__file__)

drop         = redis.register_script(open(os.path.join(SCRIPT_PATH, './drop.lua')).read())
device_motion = redis.register_script(open(os.path.join(SCRIPT_PATH, './device_motion.lua')).read())
text_search  = redis.register_script(open(os.path.join(SCRIPT_PATH, './text_search.lua')).read())
allow        = redis.register_script(open(os.path.join(SCRIPT_PATH, './allow.lua')).read())
is_allowed   = redis.register_script(open(os.path.join(SCRIPT_PATH, './is_allowed.lua')).read())
clear_related_permissions = redis.register_script(open(os.path.join(SCRIPT_PATH, './clear_related_permissions.lua')).read())

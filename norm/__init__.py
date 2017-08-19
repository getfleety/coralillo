import redis
from norm.lua import Lua


class Engine:

    def __init__(self, **kwargs):
        self.redis = redis.StrictRedis(**kwargs)

        self.lua = Lua(self.redis)


def create_engine(**kwargs):
    return Engine(**kwargs)

from norm.core import Model, BoundedModel

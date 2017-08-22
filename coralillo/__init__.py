import redis
from coralillo.lua import Lua


class Engine:

    def __init__(self, **kwargs):
        try:
            url = kwargs.pop('url')

            self.redis = redis.StrictRedis.from_url(url)
        except:
            self.redis = redis.StrictRedis(**kwargs)

        self.lua = Lua(self.redis)


from coralillo.core import Form, Model, BoundedModel

import redis
from coralillo.lua import Lua
from uuid import uuid1


def uuid1_id():
    return uuid1().hex


class Engine:

    def __init__(self, id_function=uuid1_id, **kwargs):
        try:
            url = kwargs.pop('url')

            self.redis = redis.StrictRedis.from_url(url, **kwargs)
        except:
            self.redis = redis.StrictRedis(**kwargs)

        self.id_function = id_function

        self.lua = Lua(self.redis)


from coralillo.core import Form, Model, BoundedModel

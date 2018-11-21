import redis
from coralillo.lua import Lua
from uuid import uuid1
from coralillo.core import Form, Model, BoundedModel

__all__ = ['Form', 'Model', 'BoundedModel', 'Engine']


def uuid1_id():
    return uuid1().hex


class Engine:

    _is_coralillo_engine = True

    def __init__(self, id_function=uuid1_id, **kwargs):
        if 'url' in kwargs:
            url = kwargs.pop('url')

            self.redis = redis.Redis.from_url(url, **kwargs)
        else:
            self.redis = redis.Redis(**kwargs)

        self.id_function = id_function

        self.lua = Lua(self.redis)

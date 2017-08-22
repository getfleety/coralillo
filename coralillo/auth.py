from coralillo.datamodel import debyte_set

from inspect import isclass
import re


class PermissionHolder:

    def allow_key(self):
        ''' Gets the key associated with this user where we store permission
        information '''
        return self.key() + ':allow'

    def allow(self, objspec, engine):
        return engine.lua.allow(keys=[self.allow_key()], args=[objspec])

    def is_allowed(self, objspec, engine, *, tail=None):
        return engine.lua.is_allowed(keys=[self.allow_key()], args=[objspec, tail])

    def revoke(self, objspec, engine):
        engine.redis.srem(self.allow_key(), objspec)

    def get_perms(self, engine):
        return debyte_set(engine.redis.smembers(self.allow_key()))

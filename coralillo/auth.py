from coralillo.datamodel import debyte_set


class PermissionHolder:

    def allow_key(self):
        ''' Gets the key associated with this user where we store permission
        information '''
        return self.key() + ':allow'

    def allow(self, objspec):
        engine = type(self).get_engine()

        return engine.lua.allow(keys=[self.allow_key()], args=[objspec])

    def is_allowed(self, objspec, *, tail=None):
        engine = type(self).get_engine()

        return engine.lua.is_allowed(keys=[self.allow_key()], args=[objspec, tail])

    def revoke(self, objspec):
        engine = type(self).get_engine()

        return engine.redis.srem(self.allow_key(), objspec)

    def get_perms(self):
        engine = type(self).get_engine()

        return debyte_set(engine.redis.smembers(self.allow_key()))

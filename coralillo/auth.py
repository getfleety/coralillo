from coralillo.datamodel import debyte_set


class PermissionHolder:

    def allow_key(self):
        ''' Gets the key associated with this user where we store permission
        information '''
        return '{}:{}:allow'.format(self.cls_key(), self.id)

    def allow(self, objspec):
        assert type(objspec) == str, 'objspec must be a string'
        engine = type(self).get_engine()

        pieces = objspec.split('/')
        restrict = pieces[1] if len(pieces) == 2 else None

        return engine.lua.allow(keys=[self.allow_key()], args=[pieces[0], restrict])

    def is_allowed(self, objspec):
        assert type(objspec) == str, 'objspec must be a string'
        engine = type(self).get_engine()

        pieces = objspec.split('/')
        restrict = pieces[1] if len(pieces) == 2 else None

        return engine.lua.is_allowed(keys=[self.allow_key()], args=[pieces[0], restrict])

    def revoke(self, objspec):
        assert type(objspec) == str, 'objspec must be a string'
        engine = type(self).get_engine()

        return engine.redis.srem(self.allow_key(), objspec)

    def get_perms(self):
        engine = type(self).get_engine()

        return debyte_set(engine.redis.smembers(self.allow_key()))

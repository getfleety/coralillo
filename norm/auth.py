from norm.datamodel import debyte_set

from inspect import isclass
import re


class PermissionHolder:

    def allow_key(self):
        ''' Gets the key associated with this user where we store permission
        information '''
        return self.key() + ':allow'

    def allow(self, objspec):
        return allow_script(keys=[self.allow_key()], args=[objspec])

    def is_allowed(self, objspec, tail=None):
        return is_allowed_script(keys=[self.allow_key()], args=[objspec, tail])

    def revoke(self, objspec):
        redis.srem(self.allow_key(), objspec)

    def get_perms(self):
        return debyte_set(redis.smembers(self.allow_key()))
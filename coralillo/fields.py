from .hashing import make_password, is_hashed
from .errors import MissingFieldError, InvalidFieldError, ReservedFieldError, NotUniqueFieldError, DeleteRestrictedError
from .datamodel import debyte_string, debyte_hash
from . import datamodel
from importlib import import_module
from .utils import to_pipeline
import re
import datetime
import json


class Field:
    ''' Defines a field of a model. Represents how to store this specific
    datatype in the redis database '''

    def __init__(self, *, name=None, index=False, required=True, default=None, private=False, regex=None, forbidden=None, allowed=None, fillable=True):
        # This field's value is mapped to the ID in a redis hash so you can Model.get_by(field, value)
        self.index     = index     

        # This field is required in validation
        self.required  = required  

        # This field's default value
        self.default   = default   

        # This field's value is not published in the JSON representation of the object
        self.private   = private   

        # A regular expresion that validates this field's value
        self.regex     = regex     

        # A set of forbidden values for this field
        self.forbidden = forbidden

        # The set of only allowed valies for this field
        self.allowed = allowed

        # This field can't be set via http
        self.fillable  = fillable  

        # This will be set later by the proxy
        self.name      = name
        self.obj       = None

    def value_or_default(self, value):
        ''' Returns the given value or the specified default value for this
        field '''
        if value is None:
            if callable(self.default):
                return self.default()
            else:
                return self.default

        return value

    def validate_required(self, value):
        ''' Validates the given value agains this field's 'required' property
        '''
        if self.required and (value is None or value==''):
            raise MissingFieldError(self.name)

    def init(self, value):
        ''' Returns the value that will be set in the model when it is passed
        as an __init__ attribute '''
        return self.value_or_default(value)

    def recover(self, data, redis=None):
        ''' Retrieve this field's value from the database '''
        value = data.get(self.name)

        if value is None or value == 'None':
            return None

        return str(value)

    def prepare(self, value):
        ''' Prepare this field's value to insert in database '''
        if value is None: return None

        return str(value)

    def to_json(self, value):
        ''' Format the value to be presented in json format '''
        return value

    def save(self, value, redis, *, commit=True):
        ''' Sets this fields value in the databse '''
        value = self.prepare(value)

        if value is not None:
            redis.hset(self.obj.key(), self.name, value)
        else:
            redis.hdel(self.obj.key(), self.name)

        if self.index:
            key = self.key()

            if self.name in self.obj._old:
                redis.hdel(key, self.obj._old[self.name])

            redis.hset(key, value, self.obj.id)

    def delete(self, redis):
        ''' Deletes this field's value from the databse. Should be implemented
        in special cases '''
        if self.index:
            redis.hdel(self.key(), getattr(self.obj, self.name))

    def validate(self, value, redis):
        '''
        Validates data obtained from a request and returns it in the apropiate
        format
        '''
        # cleanup
        if type(value) == str:
            value = value.strip()

        value = self.value_or_default(value)

        # validation
        self.validate_required(value)

        if self.regex and not re.match(self.regex, value, flags=re.ASCII):
            raise InvalidFieldError(self.name)

        if self.forbidden and value in self.forbidden:
            raise ReservedFieldError(self.name)

        if self.allowed and value not in self.allowed:
            raise InvalidFieldError(self.name)

        if self.index:
            key = self.key()

            old = debyte_string(redis.hget(key, value))
            old_value = getattr(self.obj, self.name)

            if old is not None and old != self.obj.id:
                raise NotUniqueFieldError(self.name)
            elif old_value != value:
                self.obj._old[self.name] = old_value

        return value

    def key(self):
        return self.obj.cls_key() + ':index_' + self.name


class Text(Field):
    pass


class TreeIndex(Field):

    def save(self, value, redis, *, commit=True):
        ''' Sets this fields value in the databse '''
        value = self.prepare(value)

        if value is not None:
            redis.hset(self.obj.key(), self.name, value)
        else:
            redis.hdel(self.obj.key(), self.name)

        key = self.key()

        if self.name in self.obj._old:
            redis.hdel(key, self.obj._old[self.name])

        redis.sadd(key + ':' + value, self.obj.id)

    def delete(self, redis):
        ''' Deletes this field's value from the databse. Should be implemented
        in special cases '''
        value = getattr(self.obj, self.name)
        redis.srem(self.key() + ':' + value, self.obj.id)

    def key(self):
        return self.obj.cls_key() + ':tree_' + self.name


class Hash(Text):
    ''' A value that should be stored as a hash, for example a password '''

    def init(self, value):
        ''' hash passwords given in the constructor '''
        value = self.value_or_default(value)

        if value is None: return None

        if is_hashed(value):
            return value

        return make_password(value)

    def prepare(self, value):
        ''' Prepare this field's value to insert in database '''
        if value is None:
            return None

        if is_hashed(value):
            return value

        return make_password(value)

    def validate(self, value, redis):
        ''' hash passwords given via http '''
        value = super().validate(value, redis)

        if is_hashed(value):
            return value

        return make_password(value)


class Bool(Field):
    ''' A boolean value '''

    def validate(self, value, redis):
        value = self.value_or_default(value)

        if value is None: return None

        if type(value) == bool:
            return value

        return value == 'true' or value == '1'

    def prepare(self, value):
        return str(value)

    def recover(self, data, redis=None):
        value = data.get(self.name)

        if value is None or value == 'None':
            return None

        return value in ['True', 'true', '1', 1]


class Integer(Field):
    ''' An integer value '''

    def validate(self, value, redis):
        value = self.value_or_default(value)

        self.validate_required(value)

        if value != 0 and not value:
            return None

        try:
            return int(value)
        except ValueError:
            raise InvalidFieldError(self.name)

    def recover(self, data, redis=None):
        value = data.get(self.name)

        if value == '' or value is None or value == 'None':
            return None

        return int(value)

    def prepare(self, value):
        return str(value)


class Float(Field):

    def validate(self, value, redis):
        value = self.value_or_default(value)

        self.validate_required(value)

        try:
            return float(value)
        except ValueError:
            raise InvalidFieldError(self.name)

    def recover(self, data, redis=None):
        value = data.get(self.name)

        if value == '' or value is None or value == 'None':
            return None

        return float(value)

    def prepare(self, value):
        return str(value)


class Datetime(Field):
    ''' A datetime that can be used transparently as such in the model '''

    def validate(self, value, redis):
        '''
        Validates data obtained from a request in ISO 8061 and returns it in Datetime data type
        '''

        value = self.value_or_default(value)

        self.validate_required(value)

        if value is None:
            return None

        if type(value) == str:
            try:
                value = datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
            except ValueError:
                raise InvalidFieldError(self.name)

        return value

    def recover(self, data, redis=None):
        value = data.get(self.name)

        if not value or value == 'None':
            return None

        return datetime.datetime.utcfromtimestamp(int(value))

    def prepare(self, value):
        if value is None:
            return None

        return str(int(value.timestamp()))

    def to_json(self, value):
        if value is None:
            return None

        return value.replace(microsecond=0).isoformat() + 'Z'


class Location(Field):
    ''' A geolocation '''

    def prepare(self, value):
        return value

    def save(self, value, redis, *, commit=True):
        key = self.key()

        if value is not None:
            redis.geoadd(key, value.lon, value.lat, self.obj.id)
        else:
            redis.zrem(key, self.obj.id)

    def delete(self, redis):
        key = self.key()

        redis.zrem(key, self.obj.id)

    def to_json(self, value):
        if value is None:
            return None

        return value.to_json()

    def recover(self, data, redis):
        key = self.key()

        try: # TODO change this once the GEO api is stable in redis-py
            value = redis.geopos(key, self.obj.id)
        except TypeError:
            value = None

        if not value:
            return None

        if value[0] is None:
            return None

        return datamodel.Location(*value[0])

    def validate(self, value, redis):
        value = self.value_or_default(value)

        self.validate_required(value)

        if value is None:
            return None

        try:
            lon, lat = map(float, value.split(','))

            assert -180 < lon < 180
            assert -90 < lat < 90

            return datamodel.Location(lon, lat)
        except:
            raise InvalidFieldError(self.name)

    def key(self):
        return self.obj.cls_key() + ':geo_' + self.name


class Dict(Field):
    ''' A dict that can be used transparently as such in the model '''

    def validate(self, value, redis):
        if not value:
            return dict()

        try:
            value = json.loads(value)
        except json.decoder.JSONDecodeError as e:
            raise InvalidFieldError(self.name)

        return value

    def prepare(self, value):
        return value

    def save(self, value, redis, *, commit=True):
        key = self.key()

        if bool(value) is not False:
            redis.delete(key)
            redis.hmset(key, value)
        else:
            redis.delete(key)

    def delete(self, redis):
        key = self.key()

        redis.delete(key)

    def to_json(self, value):
        if value is None:
            return dict()

        return value

    def recover(self, data, redis):
        key = self.key()

        try:
            value = debyte_hash(redis.hgetall(key))
        except TypeError:
            value = dict()

        return value

    def key(self):
        return '{}:{}:dict_{}'.format(self.obj.cls_key(), self.obj.id, self.name)


class Relation(Field):

    def __init__(self, model, *, private=False, on_delete=None, inverse=None):
        self.modelspec = model
        self.private   = private
        self.on_delete = on_delete
        self.inverse   = inverse
        self.fillable  = False

    def model(self):
        if type(self.modelspec) == str:
            from . import Model

            pieces = self.modelspec.split('.')

            return getattr(import_module('.'.join(pieces[:-1])), pieces[-1])

        return self.modelspec


class ForeignIdRelation(Relation):

    def __init__(self, model, *, private=False, on_delete=None, inverse=None):
        super().__init__(model, private=private, on_delete=on_delete, inverse=inverse)
        self.default   = None

    def relate(self, obj, pipeline):
        pipeline.hset(self.obj.key(), self.name, obj.id)

    def unrelate(self, obj, redis):
        redis.hdel(self.obj.key(), self.name, obj.id)

    def set(self, value, *, commit=True):
        redis = type(self.obj).get_redis()
        getattr(self.obj.proxy, self.name).fill()

        prev = getattr(self.obj, self.name)

        if prev is not None:
            getattr(prev.proxy, self.inverse).unrelate(self.obj, redis)

        if value is None:
            redis.hdel(self.obj.key(), self.name)
            setattr(self.obj, self.name, None)
            return

        redis.hset(self.obj.key(), self.name, value.id)

        related = value

        if self.inverse:
            getattr(related.proxy, self.inverse).relate(self.obj, redis)

        setattr(self.obj, self.name, value)

    def delete(self, redis):
        getattr(self.obj.proxy, self.name).fill()
        item = getattr(self.obj, self.name)

        if item is None: return

        if self.on_delete == 'restrict':
            raise DeleteRestrictedError('attempt to delete with relations and restrict flag')

        if self.on_delete == 'cascade':
            item.delete()
        elif self.inverse:
            getattr(item.proxy, self.inverse).unrelate(self.obj, redis)

    def fill(self):
        setattr(self.obj, self.name, self.get())

    def get(self):
        redis = type(self.obj).get_redis()
        value = debyte_string(redis.hget(self.obj.key(), self.name))

        return self.model().get(value)


class MultipleRelation(Relation):

    def relate_all(self, value, pipe):
        raise NotImplementedError('must be implemented in subclass')

    def set(self, value, *, commit=True):
        key  = self.key()
        redis = type(self.obj).get_redis()
        pipe = to_pipeline(redis)

        pipe.delete(key)

        if type(value) != list or len(value) == 0:
            setattr(self.obj, self.name, [])
            return

        self.relate_all(value, pipe)

        for related in value:
            if self.inverse:
                getattr(related.proxy, self.inverse).relate(self.obj, pipe)

        if commit:
            pipe.execute()

        setattr(self.obj, self.name, value)

    def add(self, value):
        redis = type(self.obj).get_redis()

        self.relate(value, redis)

        if self.inverse:
            getattr(value.proxy, self.inverse).relate(self.obj, redis)

    def recover(self, data, redis=None):
        ''' Don't read the database by default '''
        return []

    def prepare(self, value):
        return value

    def init(self,value):
        proposed = self.value_or_default(value)

        if not proposed:
            return []
        return proposed

    def fill(self, **kwargs):
        ''' Loads the relationships into this model. They are not loaded by
        default '''
        setattr(self.obj, self.name, self.get(**kwargs))

    def get(self, **kwargs):
        ''' Returns this relation '''
        redis = type(self.obj).get_redis()
        related = list(map(
            lambda id : self.model().get(debyte_string(id)),
            self.get_related_ids(redis, **kwargs)
        ))

        return related

    def delete(self, redis):
        key = self.key()

        getattr(self.obj.proxy, self.name).fill()
        items = getattr(self.obj, self.name)

        if self.on_delete == 'restrict' and len(items) > 0:
            raise DeleteRestrictedError('attempt to delete with relations and restrict flag')

        for item in items:
            if self.on_delete == 'cascade':
                item.delete()
            elif self.inverse:
                getattr(item.proxy, self.inverse).unrelate(self.obj, redis)

        redis.delete(key)

    def remove(self, value):
        redis = type(self.obj).get_redis()

        self.unrelate(value, redis)

        if self.inverse:
            getattr(value.proxy, self.inverse).unrelate(self.obj, redis)

    def count(self):
        raise NotImplementedError('count is not implemented for this subclass of MultipleRelation')


class SetRelation(MultipleRelation):
    ''' A relationship with another model '''

    def __init__(self, model, *, private=False, on_delete=None, inverse=None):
        super().__init__(model, private=private, on_delete=on_delete, inverse=inverse)
        self.default   = []
        self.fillable  = False

    def key(self):
        return '{}:{}:srel_{}'.format(self.obj.cls_key(), self.obj.id, self.name)

    def relate(self, obj, redis):
        redis.sadd(self.key(), obj.id)

    def relate_all(self, value, redis):
        redis.sadd(self.key(), *[r.id for r in value])

    def unrelate(self, obj, redis):
        redis.srem(self.key(), obj.id)

    def get_related_ids(self, redis):
        key = self.key()

        return redis.smembers(key)

    def count(self):
        key   = self.key()
        redis = type(self.obj).get_redis()

        return redis.scard(key)

    def __contains__(self, item):
        if not isinstance(item, self.model()):
            return False

        redis = type(self.obj).get_redis()

        return redis.sismember(self.key(), item.id)


class SortedSetRelation(MultipleRelation):
    ''' A relationship with another model that ensures the same ordering every
    time '''

    def __init__(self, model, sort_key, **kwargs):
        super().__init__(model, **kwargs)
        self.sort_key = sort_key
        self.default   = []
        self.fillable  = False

    def key(self):
        return '{}:{}:zrel_{}'.format(self.obj.cls_key(), self.obj.id, self.name)

    def relate(self, obj, redis):
        field = getattr(self.model(), self.sort_key) # the field in the foreign model

        redis.zadd(self.key(), field.prepare(getattr(obj, self.sort_key)), obj.id)

    def relate_all(self, value, redis):
        field = getattr(self.model(), self.sort_key) # the field in the foreign model

        p = lambda v: int(field.prepare(getattr(v, self.sort_key)))

        redis.zadd(self.key(), *sum(([p(r), r.id] for r in value), []))

    def unrelate(self, obj, redis):
        redis.zrem(self.key(), obj.id)

    def get_related_ids(self, redis, *, score=None):
        key = self.key()

        if score:
            return redis.zrangebyscore(key, *score)

        return redis.zrange(key, 0, -1)

    def count(self):
        key   = self.key()
        redis = type(self.obj).get_redis()

        return redis.zcard(key)

    def __contains__(self, item):
        if not isinstance(item, self.model()):
            return False

        redis = type(self.obj).get_redis()

        return redis.zscore(self.key(), item.id) is not None

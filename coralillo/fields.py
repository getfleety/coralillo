from . import datamodel
from .datamodel import debyte_string, debyte_hash
from .errors import MissingFieldError, InvalidFieldError, ReservedFieldError, NotUniqueFieldError, DeleteRestrictedError
from .hashing import make_password, is_hashed
from .utils import to_pipeline
from coralillo.queryset import QuerySet
from importlib import import_module
import datetime
import json
import re


class Field:
    ''' Defines a field of a model. Represents how to store this specific
    datatype in the redis database '''

    def __init__(self, *, name=None, index=False, required=True, default=None, private=False, regex=None, forbidden=None, allowed=None, fillable=True):
        # This field's value is mapped to the ID in a redis hash so you can Model.get_by(field, value)
        self.index = index

        # This field is required in validation
        self.required = required

        # This field's default value
        self.default = default

        # This field's value is not published in the JSON representation of the object
        self.private = private

        # A regular expresion that validates this field's value
        self.regex = regex

        # A set of forbidden values for this field
        self.forbidden = forbidden

        # The set of only allowed valies for this field
        self.allowed = allowed

        # This field can't be set via http
        self.fillable = fillable

        self.name = name

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self

        if isinstance(self, MultipleRelation):
            return RelationManager

        return instance.__dict__[self.name]

    def __set__(self, instance, value):
        instance.__dict__[self.name] = value

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

    def recover(self, instance, data, redis):
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

    def save(self, instance, value, redis):
        ''' Sets this field's value in the databse '''
        value = self.prepare(value)

        if value is not None:
            redis.hset(instance.key(), self.name, value)
        else:
            redis.hdel(instance.key(), self.name)

        if self.index:
            key = self.key(instance)

            if self.name in instance._old:
                redis.hdel(key, instance._old[self.name])

            if value is not None:
                redis.hset(key, value, instance.id)

    def delete(self, instance, redis):
        ''' Deletes this field's value from the databse. Should be implemented
        in special cases '''
        if self.index:
            redis.hdel(self.key(instance), getattr(instance, self.name))

    def validate(self, instance, value, redis):
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
            key = self.key(instance)

            old = debyte_string(redis.hget(key, value)) if value is not None else None
            old_value = getattr(instance, self.name)

            if old is not None and old != instance.id:
                raise NotUniqueFieldError(self.name)
            elif old_value != value:
                instance._old[self.name] = old_value

        return value

    def key(self, obj):
        return obj.cls_key() + ':index_' + self.name


class Text(Field):
    pass


class TreeIndex(Field):

    def save(self, instance, value, redis):
        ''' Sets this fields value in the databse '''
        value = self.prepare(value)

        if value is not None:
            redis.hset(instance.key(), self.name, value)
        else:
            redis.hdel(instance.key(), self.name)

        key = self.key(instance)

        if self.name in instance._old:
            redis.hdel(key, instance._old[self.name])

        redis.sadd(key + ':' + value, instance.id)

    def delete(self, instance, redis):
        ''' Deletes this field's value from the databse. Should be implemented
        in special cases '''
        value = getattr(instance, self.name)
        redis.srem(self.key(instance) + ':' + value, instance.id)

    def key(self, obj):
        return obj.cls_key() + ':tree_' + self.name


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

    def validate(self, instance, value, redis):
        ''' hash passwords given via http '''
        value = super().validate(instance, value, redis)

        if is_hashed(value):
            return value

        return make_password(value)


class Bool(Field):
    ''' A boolean value '''

    def validate(self, instance, value, redis):
        value = self.value_or_default(value)

        if value is None: return None

        if type(value) == bool:
            return value

        return value == 'true' or value == '1'

    def prepare(self, value):
        return str(value)

    def recover(self, instance, data, redis):
        value = data.get(self.name)

        if value is None or value == 'None':
            return None

        return value in ['True', 'true', '1', 1]


class Integer(Field):
    ''' An integer value '''

    def validate(self, instance, value, redis):
        value = self.value_or_default(value)

        self.validate_required(value)

        if value != 0 and not value:
            return None

        try:
            return int(value)
        except ValueError:
            raise InvalidFieldError(self.name)

    def recover(self, instance, data, redis):
        value = data.get(self.name)

        if value == '' or value is None or value == 'None':
            return None

        return int(value)

    def prepare(self, value):
        return str(value)


class Float(Field):

    def validate(self, instance, value, redis):
        value = self.value_or_default(value)

        self.validate_required(value)

        try:
            return float(value)
        except ValueError:
            raise InvalidFieldError(self.name)

    def recover(self, instance, data, redis):
        value = data.get(self.name)

        if value == '' or value is None or value == 'None':
            return None

        return float(value)

    def prepare(self, value):
        return str(value)


class Datetime(Field):
    ''' A datetime that can be used transparently as such in the model '''

    def validate(self, instance, value, redis):
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

    def recover(self, instance, data, redis):
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

    def save(self, instance, value, redis):
        key = self.key(instance)

        if value is not None:
            redis.geoadd(key, value.lon, value.lat, instance.id)
        else:
            redis.zrem(key, instance.id)

    def delete(self, instance, redis):
        key = self.key(instance)

        redis.zrem(key, instance.id)

    def to_json(self, value):
        if value is None:
            return None

        return value.to_json()

    def recover(self, instance, data, redis):
        key = self.key(instance)
        value = redis.geopos(key, instance.id)

        if not value:
            return None

        if value[0] is None:
            return None

        return datamodel.Location(*value[0])

    def validate(self, instance, value, redis):
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

    def key(self, obj):
        return obj.cls_key() + ':geo_' + self.name


class Dict(Field):
    ''' A dict that can be used transparently as such in the model '''

    def validate(self, instance, value, redis):
        if not value:
            return dict()

        try:
            value = json.loads(value)
        except json.decoder.JSONDecodeError:
            raise InvalidFieldError(self.name)

        return value

    def prepare(self, value):
        return value

    def save(self, instance, value, redis):
        key = self.key(instance)

        if value is not None:
            redis.delete(key)
            redis.hset(key, self.name, json.dumps(value))
        else:
            redis.delete(key)

    def delete(self, instance, redis):
        key = self.key(instance)

        redis.delete(key)

    def to_json(self, value):
        if value is None:
            return dict()

        return value

    def recover(self, instance, data, redis):
        key = self.key(instance)

        try:
            value = json.loads(redis.hget(key, self.name))
        except TypeError:
            value = dict()

        return value

    def key(self, obj):
        return '{}:{}:dict_{}'.format(obj.cls_key(), obj.id, self.name)


class Relation(Field):

    def __init__(self, model, *, private=False, on_delete=None, inverse=None):
        self.index = False
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

    def save(self, instance, value, redis):
        raise NotImplementedError()


class ForeignIdRelation(Relation):

    def __init__(self, model, *, private=False, on_delete=None, inverse=None):
        super().__init__(model, private=private, on_delete=on_delete, inverse=inverse)
        self.default   = None

    def validate(self, instance, value, redis):
        if value is None:
            return None

        related_obj = self.model().get(value)

        if related_obj is None:
            raise InvalidFieldError(self.name)

        return related_obj

    def save(self, instance, value, redis):
        if value is not None:
            assert type(value) == self.model()
            redis.hset(instance.key(), self.name, value.id)

    def relate(self, self_obj, obj, pipeline):
        pipeline.hset(self_obj.key(), self.name, obj.id)

    def unrelate(self, self_obj, obj, redis):
        redis.hdel(self_obj.key(), self.name, obj.id)

    def set(self, self_obj, value, *, commit=True):
        redis = type(self_obj).get_redis()
        getattr(self_obj.proxy, self.name).fill()

        prev = getattr(self_obj, self.name)

        if prev is not None:
            getattr(prev.proxy, self.inverse).unrelate(self_obj, redis)

        if value is None:
            redis.hdel(self_obj.key(), self.name)
            setattr(self_obj, self.name, None)
            return

        redis.hset(self_obj.key(), self.name, value.id)

        related = value

        if self.inverse:
            getattr(related.proxy, self.inverse).relate(self_obj, redis)

        setattr(self_obj, self.name, value)

    def delete(self, instance, redis):
        getattr(instance.proxy, self.name).fill()
        item = getattr(instance, self.name)

        if item is None: return

        if self.on_delete == 'restrict':
            raise DeleteRestrictedError('attempt to delete with relations and restrict flag')

        if self.on_delete == 'cascade':
            item.delete()
        elif self.inverse:
            getattr(item.proxy, self.inverse).unrelate(instance, redis)

    def fill(self, self_obj):
        setattr(self_obj, self.name, self.get())

    def get(self, self_obj):
        redis = type(self_obj).get_redis()
        value = debyte_string(redis.hget(self_obj.key(), self.name))

        return self.model().get(value)


class MultipleRelation(Relation):

    def relate_all(self, value, pipe):
        raise NotImplementedError('must be implemented in subclass')

    def set(self, value, self_obj, *, commit=True):
        assert False, "rethink this API and the commit=True parameter"
        key  = self.key(instance)
        redis = type(self_obj).get_redis()
        pipe = to_pipeline(redis)

        pipe.delete(key)

        if type(value) != list or len(value) == 0:
            setattr(self_obj, self.name, [])
            return

        self.relate_all(value, pipe)

        for related in value:
            if self.inverse:
                getattr(related.proxy, self.inverse).relate(self_obj, pipe)

        if commit:
            pipe.execute()

        setattr(self_obj, self.name, value)

    def add(self, value, self_obj):
        redis = type(self_obj).get_redis()

        self.relate(value, redis)

        if self.inverse:
            getattr(value.proxy, self.inverse).relate(self_obj, redis)

    def recover(self, instance, data, redis):
        ''' Don't read the database by default '''
        return []

    def prepare(self, value):
        return value

    def init(self,value):
        proposed = self.value_or_default(value)

        if not proposed:
            return []
        return proposed

    def all(self, **kwargs):
        ''' Returns this relation '''
        redis = type(self_obj).get_redis()
        related = list(map(
            lambda id : self.model().get(debyte_string(id)),
            self.get_related_ids(redis, **kwargs)
        ))

        return related

    def delete(self, instance, redis):
        key = self.key(instance)

        getattr(self_obj.proxy, self.name).fill()
        items = getattr(self_obj, self.name)

        if self.on_delete == 'restrict' and len(items) > 0:
            raise DeleteRestrictedError('attempt to delete with relations and restrict flag')

        for item in items:
            if self.on_delete == 'cascade':
                item.delete()
            elif self.inverse:
                getattr(item.proxy, self.inverse).unrelate(self_obj, redis)

        redis.delete(key)

    def remove(self, value):
        redis = type(self_obj).get_redis()

        self.unrelate(value, redis)

        if self.inverse:
            getattr(value.proxy, self.inverse).unrelate(self_obj, redis)

    def count(self):
        raise NotImplementedError('count is not implemented yet for this subclass of MultipleRelation')

    def q(self, **kwargs):
        raise NotImplementedError('q is not implemented yet for this subclass of MultipleRelation')


class SetRelation(MultipleRelation):
    ''' A relationship with another model '''

    def __init__(self, model, *, private=False, on_delete=None, inverse=None):
        super().__init__(model, private=private, on_delete=on_delete, inverse=inverse)
        self.default   = []
        self.fillable  = False

    def key(self):
        return '{}:{}:srel_{}'.format(self_obj.cls_key(), self_obj.id, self.name)

    def save(self, instance, value, redis):
        for item in value:
            assert type(item) == self.modelspec

        for item in value:
            item.save(trigger_inverse=False)
            redis.sadd(self.key(instance), item.id)

    def relate(self, obj, redis):
        redis.sadd(self.key(instance), obj.id)

    def relate_all(self, value, redis):
        redis.sadd(self.key(instance), *[r.id for r in value])

    def unrelate(self, obj, redis):
        redis.srem(self.key(instance), obj.id)

    def get_related_ids(self, redis):
        key = self.key(instance)

        return redis.smembers(key)

    def count(self):
        key   = self.key(instance)
        redis = type(self_obj).get_redis()

        return redis.scard(key)

    def q(self):
        cls = type(self_obj)
        redis = cls.get_redis()

        return QuerySet(self.model(), redis.sscan_iter(self.key(instance)))

    def __contains__(self, item):
        if not isinstance(item, self.model()):
            return False

        redis = type(self_obj).get_redis()

        return redis.sismember(self.key(instance), item.id)


class SortedSetRelation(MultipleRelation):
    ''' A relationship with another model that ensures the same ordering every
    time '''

    def __init__(self, model, sort_key, **kwargs):
        super().__init__(model, **kwargs)
        self.sort_key = sort_key
        self.default   = []
        self.fillable  = False

    def key(self):
        return '{}:{}:zrel_{}'.format(self_obj.cls_key(), self_obj.id, self.name)

    def relate(self, obj, redis):
        field = getattr(self.model(), self.sort_key) # the field in the foreign model

        redis.zadd(self.key(instance), {
            field.prepare(getattr(obj, self.sort_key)): obj.id,
        })

    def relate_all(self, value, redis):
        field = getattr(self.model(), self.sort_key) # the field in the foreign model

        p = lambda v: int(field.prepare(getattr(v, self.sort_key)))

        redis.zadd(self.key(instance), {
            p(r): r.id
            for r in value
        })

    def unrelate(self, obj, redis):
        redis.zrem(self.key(instance), obj.id)

    def get_related_ids(self, redis, *, score=None):
        key = self.key(instance)

        if score:
            return redis.zrangebyscore(key, *score)

        return redis.zrange(key, 0, -1)

    def count(self):
        key   = self.key(instance)
        redis = type(self_obj).get_redis()

        return redis.zcard(key)

    def __contains__(self, item):
        if not isinstance(item, self.model()):
            return False

        redis = type(self_obj).get_redis()

        return redis.zscore(self.key(instance), item.id) is not None

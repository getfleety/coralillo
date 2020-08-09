from . import datamodel
from .datamodel import debyte_string
from .errors import MissingFieldError, InvalidFieldError, ReservedFieldError, NotUniqueFieldError, DeleteRestrictedError
from .hashing import make_password, is_hashed
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

        if isinstance(self, Relation):
            return self.manager(instance)

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
        if self.required and (value is None or value == ''):
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
        if value is None:
            return None

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

    def _delete(self, instance, redis):
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

    def _delete(self, instance, redis):
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

        if value is None:
            return None

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

        if value is None:
            return None

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

    def _delete(self, instance, redis):
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
        except ValueError:
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

    def _delete(self, instance, redis):
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


def model_from_spec(modelspec):
    if type(modelspec) == str:
        pieces = modelspec.split('.')

        return getattr(import_module('.'.join(pieces[:-1])), pieces[-1])

    return modelspec


class Relation(Field):

    def __init__(self, model, *, private=False, on_delete='set_null', inverse=None):
        self.index = False
        self.modelspec = model
        self.private = private
        self.on_delete = on_delete
        self.inverse = inverse
        self.fillable = False

    def _delete(self, instance, redis):
        raise NotImplementedError()


class SingleRelation(Relation):
    pass


class ForeignIdRelation(SingleRelation):

    def __init__(self, model, *, private=False, on_delete='set_null', inverse=None):
        super().__init__(model, private=private, on_delete=on_delete, inverse=inverse)
        self.default = None

    def validate(self, instance, value, redis):
        if value is None:
            return None

        related_obj = model_from_spec(self.modelspec).get(value)

        if related_obj is None:
            raise InvalidFieldError(self.name)

        return related_obj

    def save(self, instance, value, redis):
        if value is not None:
            assert type(value) == model_from_spec(self.modelspec)
            redis.hset(instance.key(), self.name, value.id)

    def _delete(self, instance, redis):
        item = getattr(instance, self.name).get()

        if item is None:
            return

        if self.on_delete == 'restrict':
            raise DeleteRestrictedError('attempt to delete with relations and restrict flag')

        if self.on_delete == 'cascade':
            item.delete()
        elif self.inverse:
            getattr(item, self.inverse)._unrelate(instance, redis)

    def manager(self, instance):
        return SingleRelationManager(instance, self.inverse, self.modelspec, self.name)


class SingleRelationManager:

    def __init__(self, instance, inverse, modelspec, name):
        self.inverse = inverse
        self.instance = instance
        self.modelspec = modelspec
        self.name = name

    def _relate(self, obj, pipeline):
        pipeline.hset(self.instance.key(), self.name, obj.id)

    def _unrelate(self, obj, redis):
        redis.hdel(self.instance.key(), self.name, obj.id)

    def get(self):
        redis = self.instance.get_redis()
        value = debyte_string(redis.hget(self.instance.key(), self.name))

        return model_from_spec(self.modelspec).get(value)

    def set(self, obj):
        redis = self.instance.get_redis()
        prev = getattr(self.instance, self.name).get()

        if prev is not None and self.inverse:
            getattr(prev.proxy, self.inverse)._unrelate(self.instance, redis)

        if obj is None:
            redis.hdel(self.instance.key(), self.name)
            setattr(self.instance, self.name, None)
            return

        redis.hset(self.instance.key(), self.name, obj.id)

        if self.inverse:
            getattr(obj, self.inverse)._relate(self.instance, redis)


class MultipleRelationManager:

    def __init__(self, instance, relation_key, inverse, modelspec):
        self.inverse = inverse
        self.instance = instance
        self.relation_key = relation_key
        self.modelspec = modelspec

    def set(self, value):
        pipe = self.instance.get_redis().pipeline()

        pipe.delete(self.relation_key)

        self._relate_all(value, pipe)

        for related in value:
            if self.inverse:
                getattr(related, self.inverse)._relate(self.instance, pipe)

        pipe.execute()

    def add(self, obj):
        assert isinstance(obj, model_from_spec(self.modelspec))
        pipe = self.instance.get_redis().pipeline()

        self._relate(obj, pipe)

        if self.inverse:
            getattr(obj, self.inverse)._relate(self.instance, pipe)

        pipe.execute()

    def all(self, **kwargs):
        ''' Returns this relation '''
        redis = self.instance.get_redis()
        related = list(map(
            lambda id: model_from_spec(self.modelspec).get(debyte_string(id)),
            self.get_related_ids(redis, **kwargs)
        ))

        return related

    def remove(self, value):
        assert isinstance(value, model_from_spec(self.modelspec))
        redis = self.instance.get_redis()

        self._unrelate(value, redis)

        if self.inverse:
            getattr(value, self.inverse)._unrelate(self.instance, redis)

    def count(self):
        raise NotImplementedError('count is not implemented yet for this subclass of MultipleRelation')

    def q(self):
        raise NotImplementedError('q is not implemented for this subclass os MultipleRelation')

    def create(self, **kwargs):
        ''' Creates a new instance of the related model and relates it to the
        current model through this field '''
        raise NotImplementedError()

    def _relate_all(self, pipeline):
        raise NotImplementedError()

    def clear(self):
        ''' Clears all the relations of this field to another model '''
        for related in self.all():
            self.remove(related)


class SetRelationManager(MultipleRelationManager):

    def _relate(self, obj, redis):
        redis.sadd(self.relation_key, obj.id)

    def _relate_all(self, value, redis):
        redis.sadd(self.relation_key, *[r.id for r in value])

    def _unrelate(self, obj, redis):
        redis.srem(self.relation_key, obj.id)

    def get_related_ids(self, redis):
        return redis.smembers(self.relation_key)

    def count(self):
        return self.instance.get_redis().scard(self.relation_key)

    def q(self):
        redis = self.instance.get_redis()

        return QuerySet(model_from_spec(self.modelspec), redis.sscan_iter(self.relation_key))

    def __contains__(self, item):
        if not isinstance(item, model_from_spec(self.modelspec)):
            return False

        return self.instance.get_redis().sismember(self.relation_key, item.id)


class SortedSetRelationManager(MultipleRelationManager):

    def __init__(self, instance, relation_key, inverse, modelspec, sort_key):
        super().__init__(instance, relation_key, inverse, modelspec)
        self.sort_key = sort_key

    def _relate(self, obj, redis):
        field = getattr(model_from_spec(self.modelspec), self.sort_key)  # the field in the foreign model

        redis.zadd(self.relation_key, {
            obj.id: int(field.prepare(getattr(obj, self.sort_key))),
        })

    def _relate_all(self, value, redis):
        field = getattr(model_from_spec(self.modelspec), self.sort_key)  # the field in the foreign model

        mapping = {
            r.id: int(field.prepare(getattr(r, self.sort_key)))
            for r in value
        }

        redis.zadd(self.relation_key, mapping)

    def _unrelate(self, obj, redis):
        redis.zrem(self.relation_key, obj.id)

    def get_related_ids(self, redis, *, score=None):
        if score:
            return redis.zrangebyscore(self.relation_key, *score)

        return redis.zrange(self.relation_key, 0, -1)

    def count(self):
        redis = self.instance.get_redis()

        return redis.zcard(self.relation_key)

    def __contains__(self, item):
        if not isinstance(item, model_from_spec(self.modelspec)):
            return False

        redis = self.instance.get_redis()

        return redis.zscore(self.relation_key, item.id) is not None


class MultipleRelation(Relation):
    ''' Indicates that this field can associate with multiple objects of some other class '''

    def manager(self):
        raise NotImplementedError('Must be implemented in subclass')

    def _delete(self, instance, redis):
        key = self.key(instance)

        items = getattr(instance, self.name).all()

        if self.on_delete == 'restrict' and len(items) > 0:
            raise DeleteRestrictedError('attempt to delete with relations and restrict flag')

        for item in items:
            if self.on_delete == 'cascade':
                item.delete()
            elif self.on_delete == 'set_null' and self.inverse:
                getattr(item, self.inverse)._unrelate(instance, redis)

        redis.delete(key)


class SetRelation(MultipleRelation):
    ''' A relationship with another model where order doesn't matter '''

    def key(self, instance):
        return '{}:{}:srel_{}'.format(instance.cls_key(), instance.id, self.name)

    def manager(self, instance):
        return SetRelationManager(instance, self.key(instance), self.inverse, self.modelspec)


class SortedSetRelation(MultipleRelation):
    ''' A relationship with another model that ensures the same ordering every
    time '''

    def __init__(self, model, sort_key, **kwargs):
        super().__init__(model, **kwargs)
        self.sort_key = sort_key

    def key(self, instance):
        return '{}:{}:zrel_{}'.format(instance.cls_key(), instance.id, self.name)

    def manager(self, instance):
        return SortedSetRelationManager(instance, self.key(instance), self.inverse, self.modelspec, self.sort_key)

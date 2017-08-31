from copy import copy
from coralillo.fields import Field, Relation, MultipleRelation, ForeignIdRelation
from coralillo.datamodel import debyte_hash, debyte_string
from coralillo.errors import ValidationErrors, UnboundModelError, BadField, ModelNotFoundError
from coralillo.utils import to_pipeline, snake_case
from coralillo.auth import PermissionHolder
from itertools import starmap
import json
import re


class Proxy:
    ''' this allows to access the Model's fields easily '''

    def __init__(self, instance):
        self.model = type(instance)
        self.instance = instance

    def __getattr__(self, name):
        field = copy(getattr(self.model, name))

        field.name = name
        field.obj = self.instance

        return field

    def __iter__(self):
        def add_attrs(ft):
            f = copy(ft[1])
            f.name = ft[0]
            f.obj = self.instance
            return (ft[0], f)

        return map(
            add_attrs,
            filter(
                lambda ft: isinstance(ft[1], Field),
                map(
                    lambda name: (name, getattr(self.model, name)),
                    filter(
                        lambda name: not name.startswith('_'),
                        dir(self.model)
                    )
                )
            )
        )


class Form:
    '''Defines an object with fields'''

    def __init__(self):
        # This allows fast queries for set relations
        self.proxy = Proxy(self)
        self._old   = dict()

    @classmethod
    def validate(cls, **kwargs):
        # catch possible errors
        errors = ValidationErrors()
        obj = cls()
        redis = cls.get_redis()

        for fieldname, field in obj.proxy:
            if not field.fillable:
                value = field.default
            else:
                try:
                    value = field.validate(kwargs.get(fieldname), redis)
                except BadField as e:
                    errors.append(e)
                    continue

            setattr(
                obj,
                fieldname,
                value
            )

        if errors.has_errors():
            raise errors

        return obj

    def __str__(self):
        return '<{} {}>'.format(type(self).__name__, ' '.join(starmap(
            lambda fn, f: '{}={}'.format(fn, repr(getattr(self, fn))),
            self.proxy,
        )))

    @classmethod
    def get_engine(cls):
        try:
            return cls.Meta.engine
        except AttributeError:
            raise UnboundModelError('The model {} is not bound to any engine'.format(cls))

    @classmethod
    def get_redis(cls):
        return cls.get_engine().redis


class Model(Form):
    '''
    Defines a model that comunicates to the Redis database
    '''

    notify = False

    def __init__(self, id=None, **kwargs):
        super().__init__()
        # Generate this object's id using the provided id function
        self.id = id if id else self.get_engine().id_function()
        self._persisted = False

        for fieldname, field in self.proxy:
            value = field.init(kwargs.get(fieldname))

            setattr(
                self,
                fieldname,
                value
            )

    def save(self):
        ''' Persists this object to the database. Each field knows how to store
        itself so we don't have to worry about it '''
        redis = type(self).get_redis()
        pipe = to_pipeline(redis)

        pipe.hset(self.key(), 'id', self.id)

        for fieldname, field in self.proxy:
            if not isinstance(field, Relation):
                field.save(getattr(self, fieldname), pipe, commit=False)

        pipe.sadd(type(self).members_key(), self.id)

        pipe.execute()

        if self.notify:
            data = json.dumps({
                'event': 'create' if not self._persisted else 'update',
                'data': self.to_json(),
            })
            redis.publish(type(self).cls_key(), data)
            redis.publish(self.key(), data)

        self._persisted = True

        return self

    def update(self, **kwargs):
        ''' validates the given data against this object's rules and then
        updates '''
        redis = type(self).get_redis()
        errors = ValidationErrors()

        for fieldname, field in self.proxy:
            if not field.fillable:
                continue

            given = kwargs.get(fieldname)

            if given is None:
                continue

            try:
                value = field.validate(kwargs.get(fieldname), redis)
            except BadField as e:
                errors.append(e)
                continue

            setattr(
                self,
                fieldname,
                value
            )

        if errors.has_errors():
            raise errors

        return self.save()

    @staticmethod
    def is_object_key(key):
        ''' checks if the given key belongs to an object. Its easy since it
        depends on the key eding like: ':obj' '''
        return re.match('^.*:obj$', key)

    @classmethod
    def get(cls, id):
        ''' Retrieves an object by id. Returns None in case of failure '''

        if not id:
            return None

        redis = cls.get_redis()
        key = '{}:{}:obj'.format(cls.cls_key(), id)

        if not redis.exists(key):
            return None

        obj = cls(id=id)
        obj._persisted = True

        data = debyte_hash(redis.hgetall(key))

        for fieldname, field in obj.proxy:
            value = field.recover(data, redis)

            setattr(
                obj,
                fieldname,
                value
            )

        return obj

    @classmethod
    def count(cls):
        ''' returns object count for this model '''
        redis = cls.get_redis()

        return redis.scard(cls.members_key())

    def reload(self):
        ''' reloads this object so if it was updated in the database it now
        contains the new values'''
        key = self.key()
        redis = type(self).get_redis()

        if not redis.exists(key):
            raise ModelNotFoundError('This object has been deleted')

        data = debyte_hash(redis.hgetall(key))

        for fieldname, field in self.proxy:
            value = field.recover(data, redis)

            setattr(
                self,
                fieldname,
                value
            )

        return self

    @classmethod
    def get_or_exception(cls, id):
        ''' Tries to retrieve an instance of this model from the database or
        raises an exception in case of failure '''
        obj = cls.get(id)

        if obj is None:
            raise ModelNotFoundError('This object does not exist in database')

        return obj

    @classmethod
    def get_by(cls, field, value):
        ''' Tries to retrieve an isinstance of this model from the database
        given a value for a defined index. Return None in case of failure '''
        redis = cls.get_redis()
        key = cls.cls_key()+':index_'+field

        id = redis.hget(key, value)

        if id:
            return cls.get(debyte_string(id))

        return None

    @classmethod
    def get_by_or_exception(cls, field, value):
        obj = cls.get_by(field, value)

        if obj is None:
            raise ModelNotFoundError('This object does not exist in database')

        return obj

    @classmethod
    def get_all(cls):
        ''' Gets all available instances of this model from the database '''
        redis = cls.get_redis()

        return list(map(
            lambda id: cls.get(id),
            list(map(
                debyte_string,
                redis.smembers(cls.members_key())
            ))
        ))

    @classmethod
    def cls_key(cls):
        ''' Returns the redis key prefix assigned to this model '''

        return snake_case(cls.__name__)

    @classmethod
    def members_key(cls):
        ''' This key holds a set whose members are the ids that exist of objects
        from this class '''
        return cls.cls_key() + ':members'

    def key(self):
        ''' Returns the redis key to access this object's values '''
        prefix = type(self).cls_key()

        return '{}:{}:obj'.format(prefix, self.id)

    def fqn(self):
        ''' Returns a fully qualified name for this object '''
        prefix = type(self).cls_key()

        return '{}:{}'.format(prefix, self.id)

    def permission(self, restrict=None):
        if restrict is None:
            return self.fqn()

        return self.fqn() + '/' + restrict

    def to_json(self, *, with_relations=True):
        ''' Serializes this model to a JSON representation so it can be sent
        via an HTTP REST API '''
        json = {
            'type': type(self).cls_key(),
            'id': self.id,
            'attributes': dict(starmap(
                lambda fn, f: (fn, f.to_json(getattr(self, fn))),
                filter(
                    lambda ft: not ft[1].private and not isinstance(ft[1], Relation),
                    self.proxy
                )
            )),
        }

        if with_relations:
            json['relations'] = dict(starmap(
                lambda fn, f: (fn, list(map(
                    lambda m: m.to_json(with_relations=False),
                    getattr(self, fn)
                ))),
                filter(
                    lambda ft: isinstance(ft[1], MultipleRelation),
                    self.proxy
                )
            ))

            json['relations'].update(dict(starmap(
                lambda fn, f: (fn, getattr(self, fn).to_json() if isinstance(getattr(self, fn), Model) else None),
                filter(
                    lambda ft: isinstance(ft[1], ForeignIdRelation),
                    self.proxy
                )
            )))
        else:
            json['relations'] = dict()

        return json

    def __eq__(self, other):
        ''' Compares this object to another. Returns true if both are of the
        same class and have the same properties. Returns false otherwise '''
        if type(self) != type(other):
            return False

        return self.id == other.id

    def delete(self):
        ''' Deletes this model from the database, calling delete in each field
        to properly delete special cases '''
        redis = type(self).get_redis()

        for fieldname, field in self.proxy:
            field.delete(redis)

        redis.delete(self.key())
        redis.srem(type(self).members_key(), self.id)

        if isinstance(self, PermissionHolder):
            redis.delete(self.allow_key())

        if self.notify:
            data = json.dumps({
                'event': 'delete',
                'data': self.to_json(),
            })
            redis.publish(type(self).cls_key(), data)
            redis.publish(self.key(), data)

        return self


class BoundedModel(Model):
    ''' A bounded model is bounded to a prefix in the database '''

    @classmethod
    def prefix(cls):
        raise NotImplementedError('Bounded models must implement the prefix function')

    @classmethod
    def cls_key(cls):
        return cls.prefix() + ':' + snake_case(cls.__name__)

from coralillo.fields import Field, Relation, MultipleRelation, SingleRelation
from coralillo.datamodel import debyte_hash, debyte_string
from coralillo.errors import ValidationErrors, UnboundModelError, BadField, ModelNotFoundError
from coralillo.utils import snake_case, parse_embed
from coralillo.auth import PermissionHolder
from coralillo.queryset import QuerySet
from coralillo import Engine
from itertools import starmap
import json
import re


def get_fields(cls):
    all_fields = dir(cls)
    not_private = filter(lambda name: not name.startswith('_'), all_fields)
    name_field_tuples = map(lambda name: (name, getattr(cls, name)), not_private)
    only_field_types = filter(lambda ft: isinstance(ft[1], Field), name_field_tuples)
    return only_field_types


def get_no_relation_fields(cls):
    return filter(lambda ft: not isinstance(ft[1], Relation), get_fields(cls))


class Form:
    ''' Parent class of the Model class, defines validation and other useful
    functions. '''

    def __init__(self):
        # This allows fast queries for set relations
        self._old = dict()

        for fieldname, field in get_fields(type(self)):
            setattr(
                self,
                fieldname,
                None
            )

    @classmethod
    def validate(cls, **kwargs):
        ''' Validates the data received as keyword arguments whose name match
        this class attributes. '''
        # errors can store multiple errors
        # obj is an instance in case validation succeeds
        # redis is needed for database validation
        errors = ValidationErrors()
        obj = cls()
        redis = cls.get_redis()

        # Check the fields
        for fieldname, field in get_fields(cls):
            if not field.fillable:
                value = field.default
            else:
                try:
                    value = field.validate(obj, kwargs.get(fieldname), redis)
                except BadField as e:
                    errors.append(e)
                    continue

            setattr(
                obj,
                fieldname,
                value
            )

        # Check for custom validation rules
        for fieldname in dir(cls):
            rule = getattr(cls, fieldname)

            if hasattr(rule, '_is_validation_rule') and rule._is_validation_rule:
                try:
                    rule(obj)
                except BadField as e:
                    errors.append(e)

        # Trigger errors if any
        if errors.has_errors():
            raise errors

        # Return the object with the new data set
        return obj

    def __str__(self):
        return '<{} {}>'.format(type(self).__name__, ' '.join(starmap(
            lambda fn, f: '{}={}'.format(fn, repr(getattr(self, fn))),
            get_fields(type(self)),
        )))

    @classmethod
    def get_engine(cls):
        try:
            return cls.Meta.engine
        except AttributeError:
            raise UnboundModelError('The model {} is not bound to any engine'.format(cls))

    @classmethod
    def set_engine(cls, neweng):
        ''' Sets the given coralillo engine so the model uses it to communicate
        with the redis database '''
        assert isinstance(neweng, Engine), 'Provided object must be of class Engine'

        if hasattr(cls, 'Meta'):
            cls.Meta.engine = neweng
        else:
            class Meta:
                engine = neweng

            cls.Meta = Meta

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

        for fieldname, field in get_no_relation_fields(type(self)):
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
        pipe = redis.pipeline()

        pipe.hset(self.key(), 'id', self.id)

        for fieldname, field in get_no_relation_fields(type(self)):
            field.save(self, getattr(self, fieldname), pipe)

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

        for fieldname, field in get_fields(type(self)):
            if not field.fillable:
                continue

            given = kwargs.get(fieldname)

            if given is None:
                continue

            try:
                value = field.validate(self, kwargs.get(fieldname), redis)
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
        depends on the key ending like: ':obj' '''
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

        for fieldname, field in get_fields(cls):
            value = field.recover(obj, data, redis)

            setattr(
                obj,
                fieldname,
                value
            )

        return obj

    @classmethod
    def q(cls, **kwargs):
        ''' Creates an iterator over the members of this class that applies the
        given filters and returns only the elements matching them '''
        redis = cls.get_redis()

        return QuerySet(cls, redis.sscan_iter(cls.members_key()))

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

        for fieldname, field in get_fields(type(self)):
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
        key = cls.cls_key() + ':index_' + field

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
    def all(cls):
        ''' Gets all available instances of this model from the database '''
        redis = cls.get_redis()

        return list(map(
            lambda id: cls.get(id),
            map(
                debyte_string,
                redis.smembers(cls.members_key())
            )
        ))

    @classmethod
    def tree_match(cls, field, string):
        ''' Given a tree index, retrieves the ids atached to the given prefix,
        think of if as a mechanism for pattern suscription, where two models
        attached to the `a`, `a:b` respectively are found by the `a:b` string,
        because both model's subscription key matches the string. '''
        if not string:
            return set()

        redis = cls.get_redis()
        prefix = '{}:tree_{}'.format(cls.cls_key(), field)
        pieces = string.split(':')

        ans = redis.sunion(
            prefix + ':' + ':'.join(pieces[0:i + 1])
            for i in range(len(pieces))
        )

        return sorted(map(
            lambda id: cls.get(id),
            map(
                debyte_string,
                ans
            )
        ), key=lambda x: x.id)

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
        ''' Returns a fully qualified key name to a permission over this object
        '''
        if restrict is None:
            return self.fqn()

        return self.fqn() + '/' + restrict

    def to_json(self, *, include=None):
        ''' Serializes this model to a JSON representation so it can be sent
        via an HTTP REST API '''
        json = dict()

        if include is None or 'id' in include or '*' in include:
            json['id'] = self.id

        if include is None or '_type' in include or '*' in include:
            json['_type'] = type(self).cls_key()

        def fieldfilter(fieldtuple):
            return \
                not fieldtuple[1].private and \
                not isinstance(fieldtuple[1], Relation) and (
                    include is None or fieldtuple[0] in include or '*' in include
                )

        json.update(dict(starmap(
            lambda fn, f: (fn, f.to_json(getattr(self, fn))),
            filter(
                fieldfilter,
                get_fields(type(self))
            )
        )))

        for relation_name, subfields in parse_embed(include):
            if not hasattr(type(self), relation_name):
                continue

            if not isinstance(getattr(type(self), relation_name), Relation):
                continue

            relation = getattr(self, relation_name)

            if isinstance(getattr(type(self), relation_name), MultipleRelation):
                json[relation_name] = list(map(lambda o: o.to_json(include=subfields), relation.all()))
            elif isinstance(getattr(type(self), relation_name), SingleRelation):
                related = relation.get()
                json[relation_name] = related.to_json(include=subfields) if related is not None else None

        return json

    def __eq__(self, other):
        ''' Compares this object to another. Returns true if both are of the
        same class and have the same properties. Returns false otherwise '''
        if type(other) == str:
            return self.id == other

        if type(self) != type(other):
            return False

        return self.id == other.id

    def delete(self):
        ''' Deletes this model from the database, calling delete in each field
        to properly delete special cases '''
        redis = type(self).get_redis()

        for fieldname, field in get_fields(type(self)):
            field._delete(self, redis)

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

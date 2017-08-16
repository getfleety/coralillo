from flask import abort
from fleety.db.orm.fields import MultipleRelation, Relation, ForeignIdRelation
from fleety.db.orm import datamodel
from fleety.db.orm.proxy import Proxy
from fleety.db.orm.errors import ImproperlyConfiguredError, ModelNotFoundError
from fleety import redis
from fleety import app
from uuid import uuid1
from itertools import starmap
from fleety.http.errors import BadRequest, MissingFieldError, NotUniqueFieldError
import datetime
import json
import re


class Form:
    '''Defines an object with fields'''

    def __init__(self):
        # This allows fast queries for set relations
        self.proxy = Proxy(self)
        self._old   = dict()

    @classmethod
    def validate(cls, **kwargs):
        # catch possible errors
        errors = MissingFieldError()
        obj = cls()

        for fieldname, field in obj.proxy:
            if not field.fillable:
                value = field.default
            else:
                try:
                    value = field.validate(kwargs.get(fieldname), redis)
                except BadRequest as e:
                    errors.concat(e)
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


class Model(Form):
    '''
    Defines a model that comunicates to the Redis database
    '''

    notify = False

    def __init__(self, id=None, **kwargs):
        super().__init__()
        # Generate this object's id using a unique 128-bit
        # check this to get the time of creation https://stackoverflow.com/questions/3795554/extract-the-time-from-a-uuid-v1-in-python
        self.id = id if id else uuid1().hex
        self._persisted = False

        for fieldname, field in self.proxy:
            value = field.init(kwargs.get(fieldname))

            setattr(
                self,
                fieldname,
                value
            )

    def save(self, *, pipeline=None, commit=True):
        ''' Persists this object to the database. Each field knows how to store
        itself so we don't have to worry about it '''
        pipe = pipeline if pipeline is not None else redis.pipeline()

        pipe.hset(self.key(), 'id', self.id)

        for fieldname, field in self.proxy:
            if not isinstance(field, Relation):
                field.save(getattr(self, fieldname), pipe, commit=commit)

        pipe.sadd(type(self).members_key(), self.id)

        if commit:
            pipe.execute()

        if self.notify:
            redis.publish(type(self).cls_key(), json.dumps({
                'event': 'create' if not self._persisted else 'update',
                'data': self.to_json(),
            }))

        self._persisted = True

        return self

    def update(self, **kwargs):
        ''' validates the given data against this object's rules and then
        updates '''
        errors = MissingFieldError()

        for fieldname, field in self.proxy:
            if not field.fillable:
                continue

            given = kwargs.get(fieldname)

            if given is None:
                continue

            try:
                value = field.validate(kwargs.get(fieldname), redis)
            except BadRequest as e:
                errors.concat(e)
                continue

            setattr(
                self,
                fieldname,
                value
            )

        if errors.has_errors():
            raise errors

        self.save()

        return self

    @staticmethod
    def is_object_key(key):
        ''' checks if the given redis key represents an object key, i.e. the
        key of a hash that maps attributes to their values.
        Currently this object keys are denoted by the ID of the object with an
        optional prefix'''
        return re.match('^[\w:]+:[a-f0-9]{32}$', key)

    @classmethod
    def get(cls, id):
        ''' Retrieves and object by id. Returns None in case of failure '''
        if not id:
            return None

        key = cls.cls_key()+':'+id

        if not redis.exists(key):
            return None

        obj = cls(id=id)
        obj._persisted = True

        data = datamodel.debyte_hash(redis.hgetall(key))

        for fieldname, field in obj.proxy:
            value = field.recover(data, redis)

            setattr(
                obj,
                fieldname,
                value
            )

        return obj

    def reload(self):
        ''' reloads this object so if it was updated in the database it now
        contains the new values'''
        key = self.key()

        if not redis.exists(key):
            raise ModelNotFoundError('This object has been deleted')

        data = datamodel.debyte_hash(redis.hgetall(key))

        for fieldname, field in self.proxy:
            value = field.recover(data, redis)

            setattr(
                self,
                fieldname,
                value
            )

        return self

    @classmethod
    def get_or_404(cls, id):
        ''' Tries to retrieve an instance of this model from the database and
        raises a 404-compatible exception in case of failure '''
        obj = cls.get(id)

        if obj is None:
            abort(404)

        return obj

    @classmethod
    def get_or_exception(cls, id):
        ''' Tries to retrieve an instance of this model from the database and
        raises a 404-compatible exception in case of failure '''
        obj = cls.get(id)

        if obj is None:
            raise ModelNotFoundError('This object does not exist in database')

        return obj

    @classmethod
    def get_by(cls, field, value):
        ''' Tries to retrieve an isinstance of this model from the database
        given a value for a defined index. Return None in case of failure '''
        key = cls.cls_key()+':index_'+field

        id = redis.hget(key, value)

        if id:
            return cls.get(datamodel.debyte_string(id))

        return None

    @classmethod
    def get_all(cls):
        ''' Gets all available instances of this model from the database '''
        pattern = cls.cls_key()+':*'

        return list(map(
            cls.get,
            map(
                datamodel.debyte_string,
                redis.smembers(cls.members_key())
            )
        ))

    @classmethod
    def cls_key(cls):
        ''' Returns the redis key prefix assigned to this model '''
        return cls.__name__.lower()

    @classmethod
    def members_key(cls):
        ''' This key holds a set whose members are the ids that exist of objects
        from this class '''
        return cls.cls_key() + ':members'

    def key(self):
        ''' Returns the redis key to access this object's values '''
        prefix = type(self).cls_key()

        return prefix+':'+self.id

    def permission(self, to=None):
        if to is None:
            return self.key()

        return self.key() + ':' + to

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
            json['relations'] = {**dict(starmap(
                lambda fn, f: (fn, list(map(
                    lambda m: m.to_json(with_relations=False),
                    getattr(self, fn)
                ))),
                filter(
                    lambda ft: isinstance(ft[1], MultipleRelation),
                    self.proxy
                )
            )), **dict(starmap(
                lambda fn, f: (fn, getattr(self, fn).to_json() if isinstance(getattr(self, fn), Model) else None),
                filter(
                    lambda ft: isinstance(ft[1], ForeignIdRelation),
                    self.proxy
                )
            ))}
        else:
            json['relations'] = dict()

        return json

    def __eq__(self, other):
        ''' Compares this object to another. Returns true if both are of the
        same class and have the same properties. Returns false otherwise '''
        if type(self) != type(other):
            return False

        return self.id == other.id

    def delete(self, pipeline=None, commit=True):
        ''' Deletes this model from the database, calling delete in each field
        to properly delete special cases '''
        pipe = pipeline if pipeline is not None else redis.pipeline()

        for fieldname, field in self.proxy:
            field.delete(pipe)

        pipe.delete(self.key())
        pipe.srem(type(self).members_key(), self.id)

        if commit:
            pipe.execute()

        if self.notify:
            # TODO reconsider pipelines in this methods or think how to trigger
            # the event when the pipeline is executed
            redis.publish(type(self).cls_key(), json.dumps({
                'event': 'delete',
                'data': self.to_json(),
            }))

        return self

class BoundedModel(Model):
    ''' A bounded model is bounded to a prefix in the database '''

    @classmethod
    def cls_key(cls):
        try:
            bound = app.config['ORGANIZATION']
        except KeyError:
            raise ImproperlyConfiguredError('Bound for bounded models not stablished')

        return bound + ':' + cls.__name__.lower()

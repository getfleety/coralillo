from copy import copy
from uuid import uuid1
from norm.fields import Field, Relation
from norm.datamodel import debyte_hash, debyte_string
from norm.errors import ValidationErrors
from redis.client import BasePipeline

def to_pipeline(redis):
    if isinstance(redis, BasePipeline):
        return redis

    return redis.pipeline()


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
        errors = MissingFieldError()
        obj = cls()

        for fieldname, field in obj.proxy:
            if not field.fillable:
                value = field.default
            else:
                try:
                    value = field.validate(kwargs.get(fieldname), redis)
                except BadField as e:
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

    def save(self, redis, *, commit=True):
        ''' Persists this object to the database. Each field knows how to store
        itself so we don't have to worry about it '''
        pipe = to_pipeline(redis)

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

    def update(self, redis, **kwargs):
        ''' validates the given data against this object's rules and then
        updates '''
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
                errors.concat(e)
                continue

            setattr(
                self,
                fieldname,
                value
            )

        if errors.has_errors():
            raise errors

        return self.save(redis)

    @staticmethod
    def is_object_key(key):
        ''' checks if the given redis key represents an object key, i.e. the
        key of a hash that maps attributes to their values.
        Currently this object keys are denoted by the ID of the object with an
        optional prefix'''
        return re.match('^[\w:]+:[a-f0-9]{32}$', key)

    @classmethod
    def get(cls, id, redis):
        ''' Retrieves an object by id. Returns None in case of failure '''
        if not id:
            return None

        key = cls.cls_key() + ':' + id

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

    def reload(self):
        ''' reloads this object so if it was updated in the database it now
        contains the new values'''
        key = self.key()

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
        ''' Tries to retrieve an instance of this model from the database and
        raises a 404-compatible exception in case of failure '''
        obj = cls.get(id)

        if obj is None:
            raise ModelNotFoundError('This object does not exist in database')

        return obj

    @classmethod
    def get_by(cls, field, value, redis):
        ''' Tries to retrieve an isinstance of this model from the database
        given a value for a defined index. Return None in case of failure '''
        key = cls.cls_key()+':index_'+field

        id = redis.hget(key, value)

        if id:
            return cls.get(debyte_string(id), redis)

        return None

    @classmethod
    def get_all(cls, redis):
        ''' Gets all available instances of this model from the database '''

        return list(map(
            lambda id: cls.get(id, redis),
            list(map(
                debyte_string,
                redis.smembers(cls.members_key())
            ))
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

        return prefix + ':' + self.id

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

    def delete(self, redis, commit=True):
        ''' Deletes this model from the database, calling delete in each field
        to properly delete special cases '''
        pipe = to_pipeline(redis)

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
    def prefix(cls):
        raise NotImplementedError('Bounded models must implement the prefix function')

    @classmethod
    def cls_key(cls):
        return cls.prefix() + ':' + cls.__name__.lower()
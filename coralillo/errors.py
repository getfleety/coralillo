import json


class ImproperlyConfiguredError(Exception): pass

class ModelNotFoundError(Exception): pass

class DeleteRestrictedError(Exception): pass

class UnboundModelError(Exception): pass


class ValidationErrors(Exception):

    def __init__(self):
        self.errors = []

    def append(self, e):
        self.errors.append(e)

    def has_errors(self):
        return len(self.errors)

    def to_json(self):
        return [e.to_json() for e in self.errors]


class BadField(Exception):

    message = '{field} is invalid'
    errorcode = 'invalid'

    def __init__(self, field='', value=''):
        assert type(field) == str, 'Field must be string'

        self.field = field
        self.value = value

    def get_detail(self):
        return self.message.format(
            field = self.field,
            value = self.value,
        )

    def to_json(self):
        return {
            'detail': self.get_detail(),
            'field': self.field,
            'i18n': 'errors.{field}.{error}'.format(
                field = self.field,
                error = self.errorcode,
            ),
        }

class MissingFieldError(BadField):
    message = '{field} is required'
    errorcode = 'required'

class InvalidFieldError(BadField):
    message = '{field} is not valid'
    errorcode = 'invalid'

class ReservedFieldError(BadField):
    message = '{field} is reserved'
    errorcode = 'reserved'

class NotUniqueFieldError(BadField):
    message = '{field} is not unique'
    errorcode = 'unique'

class ImproperlyConfiguredError(Exception): pass

class ModelNotFoundError(Exception): pass

class DeleteRestrictedError(Exception): pass

class UnboundModelError(Exception): pass


class ValidationErrors(Exception):

    def __init__(self):
        self.errors = []

    def has_errors(self):
        return len(self.errors)


class BadField(Exception): pass

class MissingFieldError(BadField): pass

class InvalidFieldError(BadField): pass

class ReservedFieldError(BadField): pass

class NotUniqueFieldError(BadField): pass

class DeleteRestrictedError(BadField): pass

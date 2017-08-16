from fleety.db.orm.fields import Field
from copy import copy


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

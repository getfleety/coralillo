from coralillo.datamodel import debyte_string

# these return false if the value is null
NULL_AFFECTED_FILTERS = ['lt', 'lte', 'gt', 'gte', 'startswith', 'endswith']
# these ones don't give a shit about null values
FILTERS = ['eq', 'ne'] + NULL_AFFECTED_FILTERS


class QuerySet:

    def __init__(self, cls, iterator):
        self.iterator = iterator
        self.filters = []
        self.cls = cls

    def __iter__(self):
        return self

    def __next__(self):
        for item in self.iterator:
            obj = self.cls.get(debyte_string(item))

            if self.matches_filters(obj):
                return obj

        raise StopIteration

    def matches_filters(self, item):
        for filt in self.filters:
            if not filt(item):
                return False

        return True

    def make_filter(self, fieldname, query_func, expct_value):
        ''' makes a filter that will be appliead to an object's property based
        on query_func '''

        def actual_filter(item):
            value = getattr(item, fieldname)

            if query_func in NULL_AFFECTED_FILTERS and value is None:
                return False

            if query_func == 'eq':
                return value == expct_value
            elif query_func == 'ne':
                return value != expct_value
            elif query_func == 'lt':
                return value < expct_value
            elif query_func == 'lte':
                return value <= expct_value
            elif query_func == 'gt':
                return value > expct_value
            elif query_func == 'gte':
                return value >= expct_value
            elif query_func == 'startswith':
                return value.startswith(expct_value)
            elif query_func == 'endswith':
                return value.endswith(expct_value)

        actual_filter.__doc__ = '{} {} {}'.format('val', query_func, expct_value)

        return actual_filter

    def filter(self, **kwargs):
        for key, value in kwargs.items():
            try:
                fieldname, query_func = key.split('__', 1)
            except ValueError:
                fieldname, query_func = key, 'eq'

            if not hasattr(self.cls, fieldname):
                raise AttributeError('Model {} does not have field {}'.format(
                    self.cls.__name__,
                    fieldname,
                ))

            if not query_func in FILTERS:
                raise AttributeError('Filter {} does not exist'.format(query_func))

            self.filters.append(self.make_filter(fieldname, query_func, value))

        return self

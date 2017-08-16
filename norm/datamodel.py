EPSILON = 0.00001

def debyte_string(byte_string):
    if type(byte_string) == bytes:
        return byte_string.decode('utf8')

    return byte_string

def debyte_iterator(iterator):
    return map(debyte_string, iterator)

def debyte_set(iterator):
    return set(debyte_iterator(iterator))

def debyte_list(iterator):
    return list(debyte_iterator(iterator))

def debyte_tuple(iterator):
    return tuple(debyte_iterator(iterator))

def debyte_float(byte_float):
    return float(byte_float)

def debyte_hash(dictlike):
    return dict(map(
        debyte_tuple,
        dictlike.items()
    ))


class Location:

    def __init__(self, lon, lat):
        self.lon = lon
        self.lat = lat

    def to_json(self):
        return {
            'lat': self.lat,
            'lon': self.lon,
        }

    def __eq__(self, other):
        if type(other) != Location:
            return False

        return abs(self.lat - other.lat)<EPSILON and abs(self.lon - other.lon)<EPSILON

    def __str__(self):
        return '<Location lat={} lon={}>'.format(self.lat, self.lon)

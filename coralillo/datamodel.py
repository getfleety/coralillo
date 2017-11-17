from math import radians, sin, cos, asin, sqrt

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

    def distance(self, loc):
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees)
        """
        assert type(loc) == type(self)

        # convert decimal degrees to radians
        lon1, lat1, lon2, lat2 = map(radians, [
            self.lon,
            self.lat,
            loc.lon,
            loc.lat,
        ])

        # haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371000 # Radius of earth in meters.
        return c * r

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

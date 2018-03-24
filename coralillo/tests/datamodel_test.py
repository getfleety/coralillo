from coralillo.datamodel import Location


def test_location():
    p1 = Location(-103.33465,20.71437)
    p2 = Location(-103.31886,20.69446)

    assert p1.distance(p2) == 2756.575438006388

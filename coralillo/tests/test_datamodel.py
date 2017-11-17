import unittest
from coralillo.datamodel import Location


class DatamodelTestCase(unittest.TestCase):

    def test_location(self):
        p1 = Location(-103.33465,20.71437)
        p2 = Location(-103.31886,20.69446)
        
        self.assertEqual(p1.distance(p2), 2756.575438006388)

if __name__ == '__main__':
    unittest.main()

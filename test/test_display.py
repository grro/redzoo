import unittest
from redzoo.math.display import duration
from datetime import datetime, timedelta



class DisplayTest(unittest.TestCase):

    def test_int(self):
        print(duration(66.8))

    def test_timedelta(self):
        yesterday = datetime.now() - timedelta(days=1)
        today = datetime.now()
        print(duration(today-yesterday))


if __name__ == '__main__':
    unittest.main()
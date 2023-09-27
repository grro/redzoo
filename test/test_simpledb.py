import unittest
from time import sleep
from typing import List
from redzoo.database.simple import SimpleDB



class SimpleDbTest(unittest.TestCase):

    def test_db(self):
        db = SimpleDB("test")
        db.put("1", 5)
        db.put("2", 8)
        self.assertIs(5, db.get("1"))
        self.assertIs(5, sorted(db.get_values())[0])
        self.assertIs(8, sorted(db.get_values())[1])

        db.clear()
        self.assertIs(0, len(db))

        db.put("3", 9, ttl_sec=1)
        db.put("4", 55, ttl_sec=1000000000)
        self.assertIs(9, db.get("3"))
        self.assertIs(55, db.get("4"))
        sleep(1.5)
        self.assertIsNone(db.get("3"))
        self.assertIs(88, db.get("3", 88))
        self.assertIs(55, db.get("4"))

    def test_dict(self):
        db = SimpleDB("liat")
        db.clear()
        db.put("1", [2])
        self.assertEqual([2], db.get("1"))

        l: List = list(db.get("1"))
        l.append(5)
        db.put("1", l)
        self.assertEqual([2, 5], db.get("1"))


def test_db_persistence(self):
        db = SimpleDB("test2")
        db.clear()
        db.put("1", 5)
        self.assertIs(5, db.get("1"))

        db = SimpleDB("test2")
        self.assertIs(5, db.get("1"))


if __name__ == '__main__':
    unittest.main()
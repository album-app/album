import unittest

from hips.core.concept.singleton import Singleton


class TestSingleton(unittest.TestCase):

    def test_singleton(self):
        # define a Subclass
        class T(metaclass=Singleton):

            def __init__(self):
                self.x = 1

        x = T()
        y = T()

        # getting all the same instances back!
        self.assertEqual(x, y)



from album.core.model.mmversion import MMVersion
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestMMVersion(TestUnitCoreCommon):

    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    def test_init(self):
        db_v_test = MMVersion(0, 1, 0)

        self.assertEqual(0, db_v_test.version)
        self.assertEqual(1, db_v_test.major)
        self.assertEqual(0, db_v_test.minor)

    def test_operators(self):
        # build input
        db_v_test_1 = MMVersion(0, 1, 0)
        db_v_test_2 = MMVersion(0, 1, 0)
        db_v_test_3 = MMVersion(0, 2, 0)
        db_v_test_4 = MMVersion(0, 1, 1)
        db_v_test_5 = MMVersion(1, 0, 0)

        # asserts and calls
        self.assertTrue(db_v_test_1 == db_v_test_2, "Two equal versions where not declared as equal!")
        self.assertFalse(db_v_test_1 == db_v_test_3, "Two different versions where declared as equal! (Mayor Version)")
        self.assertFalse(db_v_test_1 == db_v_test_4, "Two different versions where declared as equal! (Minor Version)")
        self.assertFalse(db_v_test_1 == db_v_test_5, "Two different versions where declared as equal! (Version)")

        self.assertTrue(db_v_test_1 < db_v_test_3, "Error in the less then operation!(Mayor Version)")
        self.assertTrue(db_v_test_1 < db_v_test_4, "Error in the less then operation! (Minor Version)")
        self.assertTrue(db_v_test_1 < db_v_test_5, "Error in the less then operation! (Version)")
        self.assertFalse(db_v_test_3 < db_v_test_1, "Error in the less then operation!")

        self.assertTrue(db_v_test_3 > db_v_test_1, "Error in the greater then operation! (Mayor Version)")
        self.assertTrue(db_v_test_4 > db_v_test_1, "Error in the greater then operation! (Minor Version)")
        self.assertTrue(db_v_test_5 > db_v_test_1, "Error in the greater then operation! (Version)")
        self.assertFalse(db_v_test_1 > db_v_test_3, "Error in the greater then operation!")

    def test_to_string(self):
        # build input
        v_string = "0.1.0"
        db_v_test_1 = MMVersion(0, 1, 0)

        # assert and call
        self.assertEqual(v_string, str(db_v_test_1), "Error in string cast!")

    def test_from_string(self):
        # build input
        v_string = "0.1.0"

        # call
        db_v_test_1 = MMVersion.from_string(v_string)

        # asserts
        self.assertEqual(db_v_test_1.version, 0, "Error in the version of db_version object when created from string")
        self.assertEqual(db_v_test_1.major, 1,
                         "Error in the mayor version of db_version object when created from string")
        self.assertEqual(db_v_test_1.minor, 0,
                         "Error in the minor version of db_version object when created from string")

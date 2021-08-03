from album.core.model.solutions_db import SolutionsDb
from test.unit.test_unit_common import TestUnitCommon


class TestSolutionDb(TestUnitCommon):
    def setUp(self):
        super().setUp()
        self.create_test_config()
        self.test_solutions_db = SolutionsDb()
        self.assertIsNotNone(self.test_solutions_db.get_cursor())

    def tearDown(self) -> None:
        self.test_solutions_db = None
        super().tearDown()

    def test__init___has_empty(self):
        self.assertTrue(self.test_solutions_db.is_empty())

    def test_next_id(self):
        self.test_solutions_db.add_solution(
            self.test_catalog_manager.local_catalog.id, "grp", "name", "version", None
        )

        self.assertEqual(2, self.test_solutions_db.next_id())

    def test_add_solution(self):
        catalog_id = "aNiceId"
        grp = "grp"
        name = "name"
        version = "version"
        parent_id = None

        self.test_solutions_db.add_solution(catalog_id, grp, name, version, parent_id)
        self.assertEqual(1, len(self.test_solutions_db.get_cursor().execute("SELECT * FROM installed_solutions").fetchall()))

        catalog_id = "aNiceId2"
        grp = "grp2"
        name = "name2"
        version = "version2"
        parent_id = 1

        self.test_solutions_db.add_solution(catalog_id, grp, name, version, parent_id)
        self.assertEqual(2, len(self.test_solutions_db.get_cursor().execute("SELECT * FROM installed_solutions").fetchall()))

        self.assertEqual(3, self.test_solutions_db.next_id())

    def test_get_all_solutions(self):
        self.test_solutions_db.add_solution("cat1", "grp1", "name1", "version1", None)
        self.test_solutions_db.add_solution("cat2", "grp2", "name2", "version2", None)
        self.test_solutions_db.add_solution("cat3", "grp3", "name3", "version3", None)

        r = self.test_solutions_db.get_all_solutions()

        self.assertEqual(3, len(r))
        for i in range(1, 4):
            expected = {
                "solution_id": i,
                "catalog_id": "cat%s" % str(i),
                "group": "grp%s" % str(i),
                "name": "name%s" % str(i),
                "version": "version%s" % str(i),
                "parent_id": None,
                # "installation_date": ???,  # we leave that out
                "last_execution_date": None
            }
            r[i - 1].pop("installation_date")
            self.assertDictEqual(expected, r[i - 1])

    def test_get_solution_by_id(self):
        self.test_solutions_db.add_solution("cat1", "grp1", "name1", "version1", None)
        self.test_solutions_db.add_solution("cat2", "grp2", "name2", "version2", None)
        self.test_solutions_db.add_solution("cat3", "grp3", "name3", "version3", None)

        r = self.test_solutions_db.get_solution_by_id(3)

        expected = {
            "solution_id": 3,
            "catalog_id": "cat3",
            "group": "grp3",
            "name": "name3",
            "version": "version3",
            "parent_id": None,
            # "installation_date": ???,  # we leave that out
            "last_execution_date": None
        }

        r.pop("installation_date")
        self.assertDictEqual(expected, r)

    def test_get_solution(self):
        self.test_solutions_db.add_solution(
            "catalog_id_exceptionell", "grp_exceptionell", "name_exceptionell", "version_exceptionell", 100
        )

        r = self.test_solutions_db.get_solution(
            "catalog_id_exceptionell", "grp_exceptionell", "name_exceptionell", "version_exceptionell"
        )
        r.pop("installation_date")

        expected = {
            "solution_id": 1,
            "catalog_id": "catalog_id_exceptionell",
            "group": "grp_exceptionell",
            "name": "name_exceptionell",
            "version": "version_exceptionell",
            "parent_id": 100,
            # "installation_date": ???,  # we leave that out
            "last_execution_date": None
        }

        self.assertDictEqual(expected, r)

    def test_get_solutions_by_grp_name_version(self):
        # same grp, name, version but different catalogs
        self.test_solutions_db.add_solution("cat1", "grp", "name", "version", None)
        self.test_solutions_db.add_solution("cat2", "grp", "name", "version", None)
        self.test_solutions_db.add_solution("cat3", "grp", "name", "version", None)
        self.test_solutions_db.add_solution("cat1", "grp_d", "name_d", "version_d", None)

        r = self.test_solutions_db.get_solutions_by_grp_name_version("grp", "name", "version")

        for i in range(1, 4):
            expected = {
                "solution_id": i,
                "catalog_id": "cat%s" % str(i),
                "group": "grp",
                "name": "name",
                "version": "version",
                "parent_id": None,
                # "installation_date": ???,  # we leave that out
                "last_execution_date": None
            }
            r[i-1].pop("installation_date")

            self.assertDictEqual(expected, r[i-1])

    def test_is_installed(self):
        self.test_solutions_db.add_solution("cat1", "grp", "name", "version", None)
        self.test_solutions_db.add_solution("cat2", "grp", "name", "version", None)
        self.test_solutions_db.add_solution("cat1", "grp_d", "name_d", "version_d", None)

        self.assertTrue(self.test_solutions_db.is_installed("cat1", "grp", "name", "version"))

    def test_update_solution(self):
        self.test_solutions_db.add_solution("cat1", "grp", "name", "version", None)
        self.test_solutions_db.add_solution("cat2", "grp", "name", "version", None)
        self.test_solutions_db.add_solution("cat1", "grp_d", "name_d", "version_d", None)

        r = self.test_solutions_db.get_solution_by_id(2)
        self.assertIsNone(r["last_execution_date"])

        self.test_solutions_db.update_solution("cat2", "grp", "name", "version")

        r = self.test_solutions_db.get_solution_by_id(2)
        self.assertIsNotNone(r["last_execution_date"])

    def test_remove_solution(self):
        self.test_solutions_db.add_solution("cat1", "grp", "name", "version", None)
        self.test_solutions_db.add_solution("cat2", "grp", "name", "version", None)
        self.test_solutions_db.add_solution("cat1", "grp_d", "name_d", "version_d", None)

        self.test_solutions_db.remove_solution("cat2", "grp", "name", "version")

        self.assertEqual(2, len(self.test_solutions_db.get_all_solutions()))
        self.assertEqual(4, self.test_solutions_db.next_id())

        self.test_solutions_db.remove_solution("cat1", "grp_d", "name_d", "version_d")
        self.assertEqual(1, len(self.test_solutions_db.get_all_solutions()))

        self.assertEqual(2, self.test_solutions_db.next_id())

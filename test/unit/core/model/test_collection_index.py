import unittest
from pathlib import Path

from album.core.controller.collection.solution_handler import SolutionHandler
from album.core.model.collection_index import CollectionIndex
from album.core.model.coordinates import Coordinates
from test.unit.test_unit_common import TestUnitCommon


class TestCollectionIndex(TestUnitCommon):
    def setUp(self):
        super().setUp()
        self.create_album_test_instance()

        self.test_catalog_collection = CollectionIndex(
            "test_catalog_collection", Path(self.tmp_dir.name).joinpath("test_db.db")
        )

        self.assertIsNotNone(self.test_catalog_collection.get_cursor())

    def tearDown(self) -> None:
        self.test_catalog_collection = None
        super().tearDown()

    def test__init___has_empty(self):
        self.assertTrue(self.test_catalog_collection.is_empty())

    def test_update_name_version(self):
        # reset DB cursors TODO my is this necessary?!
        self.test_catalog_collection.connections = {}
        self.test_catalog_collection.cursors = {}

        # pre-assert
        self.assertEqual("test_catalog_collection", self.test_catalog_collection.get_name())

        # call
        self.test_catalog_collection.update_name_version("myName", self.test_catalog_collection.version)

        # assert
        self.assertEqual("myName", self.test_catalog_collection.get_name())

    def test_get_name(self):
        self.test_catalog_collection.create()  # sets the name!
        self.assertEqual("test_catalog_collection", self.test_catalog_collection.get_name())

    def test_get_version(self):
        self.test_catalog_collection.create()  # sets the version!
        self.assertEqual("0.1.0", self.test_catalog_collection.get_version())

    def test_next_id(self):
        self.test_catalog_collection.create()
        next_id = self.test_catalog_collection.next_id("collection")

        self.assertEqual(1, next_id)

    def test_is_empty(self):
        self.test_catalog_collection.create()
        self.assertTrue(self.test_catalog_collection.is_empty())

    # ### catalog ###

    @unittest.skip("Needs to be implemented!")
    def test_insert_catalog(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_catalog(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_catalog_by_name(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_all_catalogs(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_remove_catalog(self):
        pass

    # ### collection ###

    def test_insert_solution(self):
        catalog_id = "aNiceId"
        grp = "grp"
        name = "name"
        version = "version"
        parent_id = None

        self.test_catalog_collection.insert_solution(catalog_id,
                                                     self._get_solution_attrs(1, grp, name, version, parent=parent_id))
        self.assertEqual(
            1, len(self.test_catalog_collection.get_cursor().execute("SELECT * FROM collection").fetchall())
        )

        catalog_id = "aNiceId2"
        grp = "grp2"
        name = "name2"
        version = "version2"
        parent_id = 1

        self.test_catalog_collection.insert_solution(catalog_id,
                                                     self._get_solution_attrs(2, grp, name, version, parent=parent_id))
        self.assertEqual(
            2, len(self.test_catalog_collection.get_cursor().execute("SELECT * FROM collection").fetchall())
        )

        self.assertEqual(3, self.test_catalog_collection.next_id("collection"))

    def test_get_all_solutions(self):
        self.test_catalog_collection.insert_solution("cat1", self._get_solution_attrs(1, "grp1", "name1", "version1"))
        self.test_catalog_collection.insert_solution("cat2", self._get_solution_attrs(2, "grp2", "name2", "version2"))
        self.test_catalog_collection.insert_solution("cat3", self._get_solution_attrs(3, "grp3", "name3", "version3"))

        r = self.test_catalog_collection.get_all_solutions()

        self.assertEqual(3, len(r))
        for i in range(1, 4):
            expected = self._get_expected_attrs({
                "collection_id": i,
                "solution_id": i,
                "catalog_id": "cat%s" % str(i),
                "group": "grp%s" % str(i),
                "name": "name%s" % str(i),
                "version": "version%s" % str(i)
            })
            r[i - 1].pop("install_date")
            r[i - 1].pop("hash")
            self.assertDictEqual(expected, r[i - 1])

    @unittest.skip("Needs to be implemented!")
    def test_get_solutions_by_catalog(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_solution_by_hash(self):
        pass

    def test_get_solution(self):
        self.test_catalog_collection.insert_solution("cat1", self._get_solution_attrs(1, "grp1", "name1", "version1"))
        self.test_catalog_collection.insert_solution("cat2", self._get_solution_attrs(2, "grp2", "name2", "version2"))
        self.test_catalog_collection.insert_solution("cat3", self._get_solution_attrs(3, "grp3", "name3", "version3"))

        r = self.test_catalog_collection.get_solution(3)

        expected = self._get_expected_attrs({
            "collection_id": 3,
            "solution_id": 3,
            "catalog_id": "cat3",
            "group": "grp3",
            "name": "name3",
            "version": "version3"
        })

        r.pop("install_date")
        r.pop("hash")

        self.assertDictEqual(expected, r)

    def test_get_solution_by_catalog_grp_name_version(self):
        self.test_catalog_collection.insert_solution(
            "catalog_id_exceptionell",
            self._get_solution_attrs(1, "grp_exceptionell", "name_exceptionell", "version_exceptionell",
                                     parent="parentDoi")
        )

        r = self.test_catalog_collection.get_solution_by_catalog_grp_name_version(
            "catalog_id_exceptionell", Coordinates("grp_exceptionell", "name_exceptionell", "version_exceptionell")
        )
        r.pop("install_date")
        r.pop("hash")

        expected = self._get_expected_attrs({
            "collection_id": 1,
            "solution_id": 1,
            "catalog_id": "catalog_id_exceptionell",
            "group": "grp_exceptionell",
            "name": "name_exceptionell",
            "version": "version_exceptionell",
            "parent": "parentDoi"
        })

        self.assertDictEqual(expected, r)

    def test_get_solutions_by_grp_name_version(self):
        # same grp, name, version but different catalogs
        self.test_catalog_collection.insert_solution("cat1", self._get_solution_attrs(1, "grp", "name", "version"))
        self.test_catalog_collection.insert_solution("cat2", self._get_solution_attrs(2, "grp", "name", "version"))
        self.test_catalog_collection.insert_solution("cat3", self._get_solution_attrs(3, "grp", "name", "version"))
        self.test_catalog_collection.insert_solution("cat1",
                                                     self._get_solution_attrs(4, "grp_d", "name_d", "version_d"))

        r = self.test_catalog_collection.get_solutions_by_grp_name_version(Coordinates("grp", "name", "version"))

        for i in range(1, 4):
            expected = self._get_expected_attrs({
                "collection_id": i,
                "solution_id": i,
                "catalog_id": "cat%s" % str(i),
                "group": "grp",
                "name": "name",
                "version": "version",
                "parent": None,
                # "installation_date": ???,  # we leave that out
                "last_execution": None
            })
            r[i - 1].pop("install_date")
            r[i - 1].pop("hash")

            self.assertDictEqual(expected, r[i - 1])

    @unittest.skip("Needs to be implemented!")
    def test_get_recently_installed_solutions(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_recently_launched_solutions(self):
        pass

    def test_update_solution(self):
        self.test_catalog_collection.insert_solution("cat1", self._get_solution_attrs(1, "grp", "name", "version"))
        self.test_catalog_collection.insert_solution("cat2", self._get_solution_attrs(2, "grp", "name", "version"))
        self.test_catalog_collection.insert_solution("cat1",
                                                     self._get_solution_attrs(3, "grp_d", "name_d", "version_d"))

        r = self.test_catalog_collection.get_solution(2)
        self.assertIsNone(r["last_execution"])

        self.test_catalog_collection.update_solution("cat2", Coordinates("grp", "name", "version"), {},
                                                     SolutionHandler.get_solution_keys())

        r = self.test_catalog_collection.get_solution(2)
        self.assertIsNotNone(r["last_execution"])

    def test_remove_solution(self):
        self.test_catalog_collection.insert_solution("cat1", self._get_solution_attrs(1, "grp", "name", "version"))
        self.test_catalog_collection.insert_solution("cat2", self._get_solution_attrs(2, "grp", "name", "version"))
        self.test_catalog_collection.insert_solution("cat1",
                                                     self._get_solution_attrs(3, "grp_d", "name_d", "version_d"))

        self.test_catalog_collection.remove_solution("cat2", Coordinates("grp", "name", "version"))

        self.assertEqual(2, len(self.test_catalog_collection.get_all_solutions()))
        self.assertEqual(4, self.test_catalog_collection.next_id("collection"))

        self.test_catalog_collection.remove_solution("cat1", Coordinates("grp_d", "name_d", "version_d"))
        self.assertEqual(1, len(self.test_catalog_collection.get_all_solutions()))

        self.assertEqual(2, self.test_catalog_collection.next_id("collection"))

    def test_is_installed(self):
        self.test_catalog_collection.insert_solution("cat1", self._get_solution_attrs(1, "grp", "name", "version"))
        self.test_catalog_collection.insert_solution("cat2", self._get_solution_attrs(2, "grp", "name", "version"))
        self.test_catalog_collection.insert_solution("cat1",
                                                     self._get_solution_attrs(3, "grp_d", "name_d", "version_d"))

        self.assertFalse(self.test_catalog_collection.is_installed("cat1", Coordinates("grp", "name", "version")))

    @unittest.skip("Needs to be implemented!")
    def test_remove_entire_catalog(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_write_version_to_yml(self):
        pass

    @staticmethod
    def _get_solution_attrs(solution_id, group, name, version, doi=None, parent=None):
        return {
            "solution_id": solution_id,
            "group": group,
            "name": name,
            "version": version,
            "title": "",
            "authors": [],
            "tags": [],
            "cite": [],
            "args": [],
            "covers": [],
            "format_version": "",
            "timestamp": "",
            "description": "",
            "git_repo": "",
            "license": "",
            "documentation": "",
            "min_album_version": "",
            "tested_album_version": "",
            "changelog": "",
            "hash": "",
            "doi": doi,
            "parent": parent
        }

    @staticmethod
    def _get_expected_attrs(attrs):
        res = {
            "collection_id": attrs["collection_id"],
            "solution_id": attrs["solution_id"],
            "catalog_id": attrs["catalog_id"],
            "group": attrs["group"],
            "name": attrs["name"],
            "version": attrs["version"],
            "parent": attrs.get("parent", None),
            "doi": attrs.get("doi", None),
            "changelog": "",
            "authors": [],
            "tags": [],
            "cite": [],
            "args": [],
            "covers": [],
            "description": "",
            "documentation": "",
            "min_album_version": "",
            "tested_album_version": "",
            "timestamp": "",
            "title": "",
            "format_version": "",
            "git_repo": "",
            "license": "",
            "installed": 0,
            # "install_date": ???,  # we leave that out
            "last_execution": None
        }
        return res

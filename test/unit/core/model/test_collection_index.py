import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from album.core.model.catalog_index import CatalogIndex
from album.core.model.collection_index import CollectionIndex
from album.runner.model.coordinates import Coordinates
from test.unit.test_unit_common import TestUnitCommon


class TestCollectionIndex(TestUnitCommon):
    def setUp(self):
        super().setUp()

        self.test_catalog_collection_index = CollectionIndex(
            "test_catalog_collection", Path(self.tmp_dir.name).joinpath("test_db.db")
        )

        self.assertIsNotNone(self.test_catalog_collection_index.get_cursor())

    def tearDown(self) -> None:
        self.test_catalog_collection_index.close()
        self.test_catalog_collection_index = None
        super().tearDown()

    def is_empty_or_full(self, empty=True):
        tc = self.test_catalog_collection_index.get_cursor()

        r = tc.execute("select * from sqlite_master;").fetchall()

        tables = []
        for row in r:
            tables.append(row["tbl_name"])

        for t in tables:
            if t != "catalog_collection":  # catalog_collection is never empty
                if empty:
                    self.assertTrue(self.test_catalog_collection_index.is_table_empty(t))
                else:
                    self.assertFalse(self.test_catalog_collection_index.is_table_empty(t))

        self.test_catalog_collection_index.close_current_connection()

    @staticmethod
    def get_test_catalog_dict(id):
        return {
            "catalog_id": id,
            "name": "myName" + str(id),
            "src": "mySrc" + str(id),
            "path": "myPath" + str(id),
            "branch_name": None,
            "deletable": True
        }

    def test__init___has_empty(self):
        self.assertTrue(self.test_catalog_collection_index.is_empty())

    def test_update_name_version(self):
        # pre-assert
        self.assertEqual("test_catalog_collection", self.test_catalog_collection_index.get_name())

        # call
        self.test_catalog_collection_index.update_name_version("myName", self.test_catalog_collection_index.version)

        # assert
        self.assertEqual("myName", self.test_catalog_collection_index.get_name())

    def test_get_name(self):
        self.test_catalog_collection_index.create()  # sets the name!
        self.assertEqual("test_catalog_collection", self.test_catalog_collection_index.get_name())

    def test_get_version(self):
        self.test_catalog_collection_index.create()  # sets the version!
        self.assertEqual("0.1.0", self.test_catalog_collection_index.get_version())

    def test_next_id(self):
        self.test_catalog_collection_index.create()
        next_id = self.test_catalog_collection_index.next_id("collection")

        self.assertEqual(1, next_id)

    def test_is_empty(self):
        self.test_catalog_collection_index.create()
        self.assertTrue(self.test_catalog_collection_index.is_empty())

    # ### catalog ###

    def test_insert_catalog(self):
        self.assertEqual([], self.test_catalog_collection_index.get_all_catalogs())

        self.test_catalog_collection_index.insert_catalog(
            "myName1", "mySrc1", "myPath1", True, None
        )

        r = self.get_test_catalog_dict(1)

        self.assertEqual([r], self.test_catalog_collection_index.get_all_catalogs())

    def test_get_catalog(self):
        self.test_catalog_collection_index.insert_catalog(
            "myName1", "mySrc1", "myPath1", True, None
        )

        r = self.get_test_catalog_dict(1)

        self.assertEqual(r, self.test_catalog_collection_index.get_catalog(1))

    def test_get_catalog_by_name(self):
        self.test_catalog_collection_index.insert_catalog(
            "myName1", "mySrc1", "myPath1", True, None
        )

        r = self.get_test_catalog_dict(1)

        self.assertEqual(r, self.test_catalog_collection_index.get_catalog_by_name("myName1"))

    def test_get_catalog_by_path(self):
        self.test_catalog_collection_index.insert_catalog(
            "myName1", "mySrc1", "myPath1", True, None
        )

        r = self.get_test_catalog_dict(1)

        self.assertEqual(r, self.test_catalog_collection_index.get_catalog_by_path("myPath1"))

    def test_get_catalog_by_src(self):
        self.test_catalog_collection_index.insert_catalog(
            "myName1", "mySrc1", "myPath1", True, None
        )

        r = self.get_test_catalog_dict(1)

        self.assertEqual(r, self.test_catalog_collection_index.get_catalog_by_src("mySrc1"))

    def test_get_all_catalogs(self):
        self.test_catalog_collection_index.insert_catalog(
            "myName1", "mySrc1", "myPath1", True, None
        )
        self.test_catalog_collection_index.insert_catalog(
            "myName2", "mySrc2", "myPath2", True, None
        )

        r = self.get_test_catalog_dict(1)

        r2 = self.get_test_catalog_dict(2)

        self.assertEqual([r, r2], self.test_catalog_collection_index.get_all_catalogs())

    @unittest.skip("Needs to be implemented!")
    def test_remove_catalog(self):
        pass

    # ### collection ###

    def test_insert_solution(self):
        catalog_id = "aNiceId"
        grp = "grp"
        name = "name"
        version = "version"

        self.test_catalog_collection_index.insert_solution(catalog_id,
                                                           self._get_solution_attrs(1, grp, name, version))
        self.assertEqual(
            1, len(self.test_catalog_collection_index.get_cursor().execute("SELECT * FROM collection").fetchall())
        )

        catalog_id = "aNiceId2"
        grp = "grp2"
        name = "name2"
        version = "version2"

        # call
        self.test_catalog_collection_index.insert_solution(catalog_id,
                                                           self._get_solution_attrs(2, grp, name, version))
        self.assertEqual(
            2, len(self.test_catalog_collection_index.get_cursor().execute("SELECT * FROM collection").fetchall())
        )

        self.assertEqual(3, self.test_catalog_collection_index.next_id("collection"))

    def test__get_children_of_solution(self):
        self.test_catalog_collection_index.insert_catalog(
            "myName1", "mySrc1", "myPath1", True, None
        )
        self.test_catalog_collection_index.insert_solution(1, self._get_solution_attrs(1, "grp", "name", "version"))
        self.test_catalog_collection_index.insert_solution(1, self._get_solution_attrs(2, "grp2", "name2", "version2"))

        # no child yet
        self.assertEqual([], self.test_catalog_collection_index._get_children_of_solution(1))
        self.assertEqual([], self.test_catalog_collection_index._get_children_of_solution(2))

        self.test_catalog_collection_index.insert_collection_collection(1, 2, 1, 1)  # now solution 2 has parent 1

        # call
        r = self.test_catalog_collection_index._get_children_of_solution(1)  # this should then be solution 2

        # assert
        self.assertEqual([2], r)

    def test_get_parent_of_solution(self):
        self.test_catalog_collection_index.insert_catalog(
            "myName1", "mySrc1", "myPath1", True, None
        )
        attrs1 = self._get_solution_attrs(1, "grp", "name", "version")
        self.test_catalog_collection_index.insert_solution(1, attrs1)
        self.test_catalog_collection_index.insert_solution(1, self._get_solution_attrs(2, "grp2", "name2", "version2"))
        self.test_catalog_collection_index.insert_solution(1, self._get_solution_attrs(3, "grp3", "name3", "version3"))

        # no parent yet
        self.assertEqual(None, self.test_catalog_collection_index.get_parent_of_solution(1))
        self.assertEqual(None, self.test_catalog_collection_index.get_parent_of_solution(2))
        self.assertEqual(None, self.test_catalog_collection_index.get_parent_of_solution(3))

        self.test_catalog_collection_index.insert_collection_collection(1, 2, 1, 1)  # now solution 2 has parent 1
        self.test_catalog_collection_index.insert_collection_collection(3, 1, 1, 1)  # now solution 1 has parent 3

        # call
        r = self.test_catalog_collection_index.get_parent_of_solution(2)

        # assert
        expected = self._get_expected_attrs({
            "collection_id": 1,
            "solution_id": 1,
            "catalog_id": 1,
            "group": "grp",
            "name": "name",
            "version": "version"
        })
        expected["children"] = [2]
        expected["parent"] = self._get_expected_attrs({
            "collection_id": 3,
            "solution_id": 3,
            "catalog_id": 1,
            "group": "grp3",
            "name": "name3",
            "version": "version3"
        })
        expected["parent"]["children"] = [1]

        r.pop("install_date")
        r.pop("installation_unfinished")
        r.pop("hash")
        r["parent"].pop("install_date")
        r["parent"].pop("installation_unfinished")
        r["parent"].pop("hash")

        # expect the parent to be recursively resolved. The children are only IDs
        self.assertEqual(expected, r)

    @unittest.skip("Needs to be implemented!")
    def test__append_metadata_to_solution(self):
        pass

    def test__get_authors_by_solution(self):
        self.test_catalog_collection_index.insert_catalog(
            "myName1", "mySrc1", "myPath1", True, None
        )
        self.test_catalog_collection_index.insert_solution(1, self._get_solution_attrs(1, "grp1", "name1", "version1", None, {'authors': []}))
        self.test_catalog_collection_index._insert_author("authorName", 1, close=False)
        self.test_catalog_collection_index._insert_author("authorName2", 1, close=False)

        self.test_catalog_collection_index._insert_collection_author(1, 1, 1)
        self.test_catalog_collection_index._insert_collection_author(1, 2, 1)

        # call
        r = self.test_catalog_collection_index._get_authors_by_solution(1)

        # assert
        self.assertEqual(["authorName", "authorName2"], r)

    def test__get_arguments_by_solution(self):
        self.test_catalog_collection_index.insert_catalog(
            "myName1", "mySrc1", "myPath1", True, None
        )
        self.test_catalog_collection_index.insert_solution(
            1, self._get_solution_attrs(1, "grp1", "name1", "version1", None, {"args": []})
        )

        argument1 = {
            "name": "myArgument",
            "type": "str",
            "description": "myDescription",
            "default_value": "myDefaultValue"
        }
        argument2 = {
            "name": "myArgument",
            "type": "str",
            "description": "myDescription",
            "default_value": "myDefaultValue"
        }

        self.test_catalog_collection_index._insert_argument(argument1, 1, close=False)
        self.test_catalog_collection_index._insert_argument(argument2, 1, close=False)

        self.test_catalog_collection_index._insert_collection_argument(1, 1, 1)
        self.test_catalog_collection_index._insert_collection_argument(1, 2, 1)

        # call
        r = self.test_catalog_collection_index._get_arguments_by_solution(1)

        # assert
        self.assertEqual([argument1, argument2], r)

    def test__get_tags_by_solution(self):
        self.test_catalog_collection_index.insert_catalog(
            "myName1", "mySrc1", "myPath1", True, None
        )
        self.test_catalog_collection_index.insert_solution(1, self._get_solution_attrs(1, "grp1", "name1", "version1", None, {"tags": []}))
        self.test_catalog_collection_index._insert_tag("myTag1", 1, close=False)
        self.test_catalog_collection_index._insert_tag("myTag2", 1, close=False)

        self.test_catalog_collection_index._insert_collection_tag(1, 1, 1)
        self.test_catalog_collection_index._insert_collection_tag(1, 2, 1)

        # call
        r = self.test_catalog_collection_index._get_tags_by_solution(1)

        # assert
        self.assertEqual(["myTag1", "myTag2"], r)

    def test__get_citations_by_solution(self):
        self.test_catalog_collection_index.insert_catalog(
            "myName1", "mySrc1", "myPath1", True, None
        )
        self.test_catalog_collection_index.insert_solution(1, self._get_solution_attrs(1, "grp1", "name1", "version1", None, {"cite": []}))

        citation1 = {
            "text": "myText",
            "doi": "myDoi"
        }
        citation2 = {
            "text": "myText2",
            # no DOI
        }
        self.test_catalog_collection_index._insert_citation(citation1, 1, close=False)
        self.test_catalog_collection_index._insert_citation(citation2, 1, close=False)

        self.test_catalog_collection_index._insert_collection_citation(1, 1, 1)
        self.test_catalog_collection_index._insert_collection_citation(1, 2, 1)

        # call
        r = self.test_catalog_collection_index._get_citations_by_solution(1)

        # assert
        self.assertEqual([citation1, citation2], r)

    def test__get_covers_by_solution(self):
        self.test_catalog_collection_index.insert_catalog(
            "myName1", "mySrc1", "myPath1", True, None
        )
        self.test_catalog_collection_index.insert_solution(1, self._get_solution_attrs(1, "grp1", "name1", "version1", None, {"covers": []}))

        cover1 = {
            "source": "mySrc",
            "description": "myDesc"
        }
        cover2 = {
            "source": "mySrc2",
            "description": "myDesc2"
        }
        self.test_catalog_collection_index._insert_cover(cover1, 1, 1, close=False)
        self.test_catalog_collection_index._insert_cover(cover2, 1, 1, close=False)

        # call
        r = self.test_catalog_collection_index._get_covers_by_solution(1)

        # assert
        self.assertEqual([cover1, cover2], r)

    def test_get_all_solutions(self):
        self.test_catalog_collection_index.insert_solution("cat1",
                                                           self._get_solution_attrs(1, "grp1", "name1", "version1"))
        self.test_catalog_collection_index.insert_solution("cat2",
                                                           self._get_solution_attrs(2, "grp2", "name2", "version2"))
        self.test_catalog_collection_index.insert_solution("cat3",
                                                           self._get_solution_attrs(3, "grp3", "name3", "version3"))

        r = self.test_catalog_collection_index.get_all_solutions()

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
            r[i - 1].pop("installation_unfinished")
            r[i - 1].pop("hash")
            self.assertDictEqual(expected, r[i - 1])

    @unittest.skip("Needs to be implemented!")
    def test_get_solutions_by_catalog(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_solution_by_hash(self):
        pass

    def test_get_solution(self):
        self.test_catalog_collection_index.insert_solution("cat1",
                                                           self._get_solution_attrs(1, "grp1", "name1", "version1"))
        self.test_catalog_collection_index.insert_solution("cat2",
                                                           self._get_solution_attrs(2, "grp2", "name2", "version2"))
        self.test_catalog_collection_index.insert_solution("cat3",
                                                           self._get_solution_attrs(3, "grp3", "name3", "version3"))

        r = self.test_catalog_collection_index.get_solution(3)

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
        r.pop("installation_unfinished")

        self.assertDictEqual(expected, r)

    @unittest.skip("Needs to be implemented!")
    def test_get_solution_by_doi(self):
        pass

    def test_get_solution_by_catalog_grp_name_version(self):
        self.test_catalog_collection_index.insert_solution(
            "catalog_id_exceptionell",
            self._get_solution_attrs(1, "grp_exceptionell", "name_exceptionell", "version_exceptionell")
        )

        r = self.test_catalog_collection_index.get_solution_by_catalog_grp_name_version(
            "catalog_id_exceptionell", Coordinates("grp_exceptionell", "name_exceptionell", "version_exceptionell")
        )
        r.pop("install_date")
        r.pop("installation_unfinished")
        r.pop("hash")

        expected = self._get_expected_attrs({
            "collection_id": 1,
            "solution_id": 1,
            "catalog_id": "catalog_id_exceptionell",
            "group": "grp_exceptionell",
            "name": "name_exceptionell",
            "version": "version_exceptionell",
        })

        self.assertDictEqual(expected, r)

    def test_get_solutions_by_grp_name_version(self):
        # same grp, name, version but different catalogs
        self.test_catalog_collection_index.insert_solution("cat1",
                                                           self._get_solution_attrs(1, "grp", "name", "version"))
        self.test_catalog_collection_index.insert_solution("cat2",
                                                           self._get_solution_attrs(2, "grp", "name", "version"))
        self.test_catalog_collection_index.insert_solution("cat3",
                                                           self._get_solution_attrs(3, "grp", "name", "version"))
        self.test_catalog_collection_index.insert_solution("cat1",
                                                           self._get_solution_attrs(4, "grp_d", "name_d", "version_d"))

        r = self.test_catalog_collection_index.get_solutions_by_grp_name_version(Coordinates("grp", "name", "version"))

        for i in range(1, 4):
            expected = self._get_expected_attrs({
                "collection_id": i,
                "solution_id": i,
                "catalog_id": "cat%s" % str(i),
                "group": "grp",
                "name": "name",
                "version": "version",
            })
            r[i - 1].pop("install_date")
            r[i - 1].pop("installation_unfinished")
            r[i - 1].pop("hash")

            self.assertDictEqual(expected, r[i - 1])

    def test_get_recently_installed_solutions(self):
        self.test_catalog_collection_index.insert_solution(
            1, self._get_solution_attrs(1, "grp", "name", "version")
        )
        self.test_catalog_collection_index.insert_solution(
            2, self._get_solution_attrs(2, "grp", "name", "version")
        )
        self.test_catalog_collection_index.insert_solution(
            1, self._get_solution_attrs(3, "grp_d", "name_d", "version_d")
        )
        self.test_catalog_collection_index.insert_solution(
            1, self._get_solution_attrs(4, "grp_u", "name_u", "version_u")
        )

        supp_attrs = {"install_date", "installed"}
        inst_date1 = datetime(1991, 6, 23, 3, 23, 44).isoformat()
        self.test_catalog_collection_index.update_solution(
            1, Coordinates("grp", "name", "version"), {"installed": 1, "install_date": inst_date1}, supp_attrs
        )
        inst_date2 = datetime(1995, 10, 29, 2, 53, 1).isoformat()
        self.test_catalog_collection_index.update_solution(
            2, Coordinates("grp", "name", "version"), {"installed": 1, "install_date": inst_date2}, supp_attrs
        )
        inst_date3 = datetime(1994, 7, 28, 7, 9, 19).isoformat()
        self.test_catalog_collection_index.update_solution(
            1, Coordinates("grp_d", "name_d", "version_d"), {"installed": 1, "install_date": inst_date3}, supp_attrs
        )
        inst_date4 = datetime(2021, 6, 14, 4, 42, 59).isoformat()
        self.test_catalog_collection_index.update_solution(
            1, Coordinates("grp_u", "name_u", "version_u"), {"installed": 0, "install_date": inst_date4}, supp_attrs
        )  # CAUTION: NOT INSTALLED, BUT WAS ONCE INSTALLED

        # call
        r = self.test_catalog_collection_index.get_recently_installed_solutions()

        # assert
        exp = [
            self._get_expected_attrs({
                "collection_id": 1,
                "solution_id": 1,
                "catalog_id": 1,
                "group": "grp",
                "name": "name",
                "version": "version",
            }),
            self._get_expected_attrs({
                "collection_id": 3,
                "solution_id": 3,
                "catalog_id": 1,
                "group": "grp_d",
                "name": "name_d",
                "version": "version_d",
            }),
            self._get_expected_attrs({
                "collection_id": 2,
                "solution_id": 2,
                "catalog_id": 2,
                "group": "grp",
                "name": "name",
                "version": "version",
            })
        ]
        exp[0]["install_date"] = inst_date1
        exp[1]["install_date"] = inst_date3
        exp[2]["install_date"] = inst_date2

        exp[0]["installed"] = 1
        exp[1]["installed"] = 1
        exp[2]["installed"] = 1

        # remove hash
        for i, _ in enumerate(r):
            r[i].pop("hash")
            r[i].pop("installation_unfinished")
            r[i]["last_execution"] = None

        self.assertEqual(exp, r)

    def test_get_recently_launched_solutions(self):
        self.test_catalog_collection_index.insert_solution(
            1, self._get_solution_attrs(1, "grp", "name", "version")
        )
        self.test_catalog_collection_index.insert_solution(
            2, self._get_solution_attrs(2, "grp", "name", "version")
        )
        self.test_catalog_collection_index.insert_solution(
            1, self._get_solution_attrs(3, "grp_d", "name_d", "version_d")
        )
        self.test_catalog_collection_index.insert_solution(
            1, self._get_solution_attrs(4, "grp_u", "name_u", "version_u")
        )

        supp_attrs = {"last_execution", "installed"}
        inst_date1 = datetime(1991, 6, 23, 3, 23, 44).isoformat()
        self.test_catalog_collection_index.update_solution(
            1, Coordinates("grp", "name", "version"), {"installed": 1, "last_execution": inst_date1}, supp_attrs
        )
        inst_date2 = datetime(1995, 10, 29, 2, 53, 1).isoformat()
        self.test_catalog_collection_index.update_solution(
            2, Coordinates("grp", "name", "version"), {"installed": 1, "last_execution": inst_date2}, supp_attrs
        )
        inst_date3 = datetime(1994, 7, 28, 7, 9, 19).isoformat()
        self.test_catalog_collection_index.update_solution(
            1, Coordinates("grp_d", "name_d", "version_d"), {"installed": 1, "last_execution": inst_date3}, supp_attrs
        )
        inst_date4 = datetime(2021, 6, 14, 4, 42, 59).isoformat()
        self.test_catalog_collection_index.update_solution(
            1, Coordinates("grp_u", "name_u", "version_u"), {"installed": 0, "last_execution": inst_date4}, supp_attrs
        )  # CAUTION: NOT INSTALLED, BUT WAS STARTED RECENTLY

        # call
        r = self.test_catalog_collection_index.get_recently_launched_solutions()

        # assert
        exp = [
            self._get_expected_attrs({
                "collection_id": 1,
                "solution_id": 1,
                "catalog_id": 1,
                "group": "grp",
                "name": "name",
                "version": "version",
            }),
            self._get_expected_attrs({
                "collection_id": 3,
                "solution_id": 3,
                "catalog_id": 1,
                "group": "grp_d",
                "name": "name_d",
                "version": "version_d",
            }),
            self._get_expected_attrs({
                "collection_id": 2,
                "solution_id": 2,
                "catalog_id": 2,
                "group": "grp",
                "name": "name",
                "version": "version",
            }),
            self._get_expected_attrs({
                "collection_id": 4,
                "solution_id": 4,
                "catalog_id": 1,
                "group": "grp_u",
                "name": "name_u",
                "version": "version_u",
            })
        ]
        exp[0]["last_execution"] = inst_date1
        exp[1]["last_execution"] = inst_date3
        exp[2]["last_execution"] = inst_date2
        exp[3]["last_execution"] = inst_date4

        exp[0]["installed"] = 1
        exp[1]["installed"] = 1
        exp[2]["installed"] = 1
        exp[3]["installed"] = 0

        # remove hash
        for i, _ in enumerate(r):
            r[i].pop("hash")
            r[i].pop("install_date")
            r[i].pop("installation_unfinished")

        self.assertEqual(exp, r)

    def test_update_solution(self):
        self.test_catalog_collection_index.insert_solution("cat1",
                                                           self._get_solution_attrs(1, "grp", "name", "version"))
        self.test_catalog_collection_index.insert_solution("cat2",
                                                           self._get_solution_attrs(2, "grp", "name", "version"))
        self.test_catalog_collection_index.insert_solution("cat1",
                                                           self._get_solution_attrs(3, "grp_d", "name_d", "version_d"))

        r = self.test_catalog_collection_index.get_solution(2)
        self.assertIsNone(r["last_execution"])

        self.test_catalog_collection_index.update_solution("cat2", Coordinates("grp", "name", "version"), {},
                                                           CatalogIndex.get_solution_column_keys())

        r = self.test_catalog_collection_index.get_solution(2)
        self.assertIsNotNone(r["last_execution"])

    def test_add_or_replace_solution(self):
        self.test_catalog_collection_index.insert_catalog(
            "myName1", "mySrc1", "myPath1", True, None
        )
        self.test_catalog_collection_index.insert_solution(1, self._get_solution_attrs(1, "grp1", "name1", "version1"))

        # mocks
        get_solution_by_catalog_grp_name_version = MagicMock()
        self.test_catalog_collection_index.get_solution_by_catalog_grp_name_version = get_solution_by_catalog_grp_name_version

        remove_solution = MagicMock()
        self.test_catalog_collection_index.remove_solution = remove_solution

        insert_solution = MagicMock()
        self.test_catalog_collection_index.insert_solution = insert_solution

        # call
        self.test_catalog_collection_index.add_or_replace_solution(
            1, Coordinates("grp1", "name1", "version1"), self.get_solution_dict()
        )

        # assert
        insert_solution.assert_called_once_with(1, self.get_solution_dict(), close=True)
        get_solution_by_catalog_grp_name_version.assert_called_once()
        remove_solution.assert_called_once_with(1, Coordinates("grp1", "name1", "version1"), close=False)

    def test_remove_solution(self):
        self.is_empty_or_full(empty=True)

        self.test_catalog_collection_index.insert_solution("cat1",
                                                           self._get_solution_attrs(1, "grp", "name", "version"))
        self.test_catalog_collection_index.insert_solution("cat2",
                                                           self._get_solution_attrs(2, "grp", "name", "version"))
        self.test_catalog_collection_index.insert_solution("cat1",
                                                           self._get_solution_attrs(3, "grp_d", "name_d", "version_d"))

        # remove second solution
        self.test_catalog_collection_index.remove_solution("cat2", Coordinates("grp", "name", "version"))

        self.assertEqual(2, len(self.test_catalog_collection_index.get_all_solutions()))
        self.assertEqual(4, self.test_catalog_collection_index.next_id("collection"))

        # remove third solution
        self.test_catalog_collection_index.remove_solution("cat1", Coordinates("grp_d", "name_d", "version_d"))
        self.assertEqual(1, len(self.test_catalog_collection_index.get_all_solutions()))

        self.assertEqual(2, self.test_catalog_collection_index.next_id("collection"))

        # remove first solution
        self.test_catalog_collection_index.remove_solution("cat1", Coordinates("grp", "name", "version"))

        # no leftovers from the solution in the DB
        self.is_empty_or_full(empty=True)

    def test_is_installed(self):
        self.test_catalog_collection_index.insert_solution("cat1",
                                                           self._get_solution_attrs(1, "grp", "name", "version"))
        self.test_catalog_collection_index.insert_solution("cat2",
                                                           self._get_solution_attrs(2, "grp", "name", "version"))
        self.test_catalog_collection_index.insert_solution("cat1",
                                                           self._get_solution_attrs(3, "grp_d", "name_d", "version_d"))

        self.assertFalse(self.test_catalog_collection_index.is_installed("cat1", Coordinates("grp", "name", "version")))

    def _get_solution_attrs(self, solution_id, group, name, version, doi=None, attrs=None):

        if attrs is None:
            attrs = {}

        d = self.get_solution_dict()

        d["solution_id"] = solution_id
        d["group"] = group
        d["name"] = name
        d["version"] = version
        d["doi"] = doi

        for attr in attrs.keys():
            d[attr] = attrs[attr]

        return d

    def _get_expected_attrs(self, attrs):
        d = self.get_solution_dict()

        d["collection_id"] = attrs["collection_id"]
        d["solution_id"] = attrs["solution_id"]
        d["catalog_id"] = attrs["catalog_id"]
        d["group"] = attrs["group"]
        d["name"] = attrs["name"]
        d["version"] = attrs["version"]
        d["doi"] = attrs.get("doi", None)

        # additional fields from collection
        d["changelog"] = None
        d["last_execution"] = None
        d["parent"] = None
        d["children"] = []
        d["installed"] = 0

        return d

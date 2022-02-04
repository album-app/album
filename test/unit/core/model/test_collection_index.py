import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from album.core.model.catalog_index import CatalogIndex
from album.core.model.collection_index import CollectionIndex
from album.runner.core.model.coordinates import Coordinates
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestCollectionIndex(TestUnitCoreCommon):
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
    def get_test_catalog_dict(catalog_id):
        return {
            "catalog_id": catalog_id,
            "name": "myName" + str(catalog_id),
            "src": "mySrc" + str(catalog_id),
            "path": "myPath" + str(catalog_id),
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
        self.assertTrue(self.test_catalog_collection_index.is_table_empty("catalog"))

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

    # ### metadata ###
    def test__insert_author(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.test_catalog_collection_index.is_table_empty("author"))

        # call
        self.test_catalog_collection_index._insert_author("myAuthor", 1)

        # assert
        self.assertFalse(self.test_catalog_collection_index.is_table_empty("author"))

    def test__insert_tag(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.test_catalog_collection_index.is_table_empty("tag"))

        # call
        self.test_catalog_collection_index._insert_tag("myTag", 1)

        # assert
        self.assertFalse(self.test_catalog_collection_index.is_table_empty("tag"))

    def test__insert_citation(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.test_catalog_collection_index.is_table_empty("citation"))

        # call
        self.test_catalog_collection_index._insert_citation({"text": "myCitation", "doi": "abc/def"}, 1)

        # assert
        self.assertFalse(self.test_catalog_collection_index.is_table_empty("citation"))

    def test__insert_argument(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.test_catalog_collection_index.is_table_empty("argument"))

        arg = {
            "name": "myName",
            "type": "myType",
            "description": "myDescription",
            "default_value": "myDefaultValue"
        }
        # call
        self.test_catalog_collection_index._insert_argument(arg, 1)

        # assert
        self.assertFalse(self.test_catalog_collection_index.is_table_empty("argument"))

    def test__insert_cover(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.test_catalog_collection_index.is_table_empty("cover"))

        # call
        self.test_catalog_collection_index._insert_cover({"source": "myCover", "description": "myDescription"}, 1, 1)

        # assert
        self.assertFalse(self.test_catalog_collection_index.is_table_empty("cover"))

    def test__insert_documentation(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.test_catalog_collection_index.is_table_empty("documentation"))

        # call
        self.test_catalog_collection_index._insert_documentation("myDocumentation", 1, 1)

        # assert
        self.assertFalse(self.test_catalog_collection_index.is_table_empty("documentation"))

    def test__exists_author(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.test_catalog_collection_index.is_table_empty("author"))

        # assert
        self.assertIsNone(self.test_catalog_collection_index._exists_author("myAuthor", 1))

        r = self.test_catalog_collection_index._insert_author("myAuthor", 1)

        self.assertEqual(r, self.test_catalog_collection_index._exists_author("myAuthor", 1))

    def test__exists_tag(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.test_catalog_collection_index.is_table_empty("tag"))

        # assert
        self.assertIsNone(self.test_catalog_collection_index._exists_tag("myTag", 1))

        r = self.test_catalog_collection_index._insert_tag("myTag", 1)

        self.assertEqual(r, self.test_catalog_collection_index._exists_tag("myTag", 1))

    def test__exists_citation(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.test_catalog_collection_index.is_table_empty("citation"))

        citation = {"text": "myCitation", "doi": "abc/def"}
        citation_minimal = {"text": "myCitationMin"}

        # assert
        self.assertIsNone(self.test_catalog_collection_index._exists_citation(citation, 1))
        self.assertIsNone(self.test_catalog_collection_index._exists_citation(citation_minimal, 1))

        r1 = self.test_catalog_collection_index._insert_citation(citation, 1)
        r2 = self.test_catalog_collection_index._insert_citation(citation_minimal, 1)

        self.assertEqual(r1, self.test_catalog_collection_index._exists_citation(citation, 1))
        self.assertEqual(r2, self.test_catalog_collection_index._exists_citation(citation_minimal, 1))

    def test__exists_argument(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.test_catalog_collection_index.is_table_empty("argument"))

        arg = {
            "name": "myName",
            "type": "myType",
            "description": "myDescription",
            "default_value": "myDefaultValue"
        }
        arg_no_type = {
            "name": "myName",
            "description": "myDescription",
            "default_value": "myDefaultValue"
        }
        arg_no_default = {
            "name": "myName",
            "type": "myType",
            "description": "myDescription"
        }
        arg_minimal = {
            "name": "myName",
            "description": "myDescription"
        }

        # assert
        self.assertIsNone(self.test_catalog_collection_index._exists_argument(arg, 1))
        self.assertIsNone(self.test_catalog_collection_index._exists_argument(arg_no_type, 1))
        self.assertIsNone(self.test_catalog_collection_index._exists_argument(arg_no_default, 1))
        self.assertIsNone(self.test_catalog_collection_index._exists_argument(arg_minimal, 1))

        r1 = self.test_catalog_collection_index._insert_argument(arg, 1)
        r2 = self.test_catalog_collection_index._insert_argument(arg_no_type, 1)
        r3 = self.test_catalog_collection_index._insert_argument(arg_no_default, 1)
        r4 = self.test_catalog_collection_index._insert_argument(arg_minimal, 1)

        self.assertEqual(r1, self.test_catalog_collection_index._exists_argument(arg, 1))
        self.assertEqual(r2, self.test_catalog_collection_index._exists_argument(arg_no_type, 1))
        self.assertEqual(r3, self.test_catalog_collection_index._exists_argument(arg_no_default, 1))
        self.assertEqual(r4, self.test_catalog_collection_index._exists_argument(arg_minimal, 1))

    def test__exists_cover(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.test_catalog_collection_index.is_table_empty("cover"))

        cover = {"source": "myCover", "description": "myDescription"}

        # assert
        self.assertIsNone(self.test_catalog_collection_index._exists_cover(cover, 1, 1))

        r = self.test_catalog_collection_index._insert_cover(cover, 1, 1)

        self.assertEqual(r, self.test_catalog_collection_index._exists_cover(cover, 1, 1))

    def test__exists_documentation(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.test_catalog_collection_index.is_table_empty("documentation"))

        # assert
        self.assertIsNone(self.test_catalog_collection_index._exists_documentation("myDocumentation", 1, 1))

        r = self.test_catalog_collection_index._insert_documentation("myDocumentation", 1, 1)

        self.assertEqual(r, self.test_catalog_collection_index._exists_documentation("myDocumentation", 1, 1))

    # ### collection/solution ###

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
        self.assertEqual(1, len(r))
        self.assertEqual(2, r[0]['collection_id_child'])

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

        # expect the parent to be recursively resolved. The children are only IDs
        self.assertEqual(1, len(r._internal['children']))
        self.assertEqual(2, r._internal['children'][0]['collection_id_child'])
        self.assertEqual(1, r._internal['collection_id'])
        self.assertEqual(1, r._internal['solution_id'])
        self.assertEqual(1, r._internal['catalog_id'])
        self.assertEqual(1, len(r._internal['parent']._internal['children']))
        self.assertEqual(1, r._internal['parent']._internal['children'][0]['collection_id_child'])
        self.assertEqual(3, r._internal['parent']._internal['collection_id'])
        self.assertEqual(3, r._internal['parent']._internal['solution_id'])
        self.assertEqual(1, r._internal['parent']._internal['catalog_id'])
        self.assertEqual('grp3', r._internal['parent']._setup['group'])
        self.assertEqual('name3', r._internal['parent']._setup['name'])
        self.assertEqual('version3', r._internal['parent']._setup['version'])

    @unittest.skip("Needs to be implemented!")
    def test__append_metadata_to_solution(self):
        pass

    def test__get_authors_by_solution(self):
        self.test_catalog_collection_index.insert_catalog(
            "myName1", "mySrc1", "myPath1", True, None
        )
        self.test_catalog_collection_index.insert_solution(1, self._get_solution_attrs(1, "grp1", "name1", "version1",
                                                                                       None, {'authors': []}))
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
        self.test_catalog_collection_index.insert_solution(1, self._get_solution_attrs(1, "grp1", "name1", "version1",
                                                                                       None, {"tags": []}))
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
        self.test_catalog_collection_index.insert_solution(1, self._get_solution_attrs(1, "grp1", "name1", "version1",
                                                                                       None, {"cite": []}))

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
        self.test_catalog_collection_index.insert_solution(1, self._get_solution_attrs(1, "grp1", "name1", "version1",
                                                                                       None, {"covers": []}))

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
            self.assertEqual(i, r[i - 1]._internal['collection_id'])
            self.assertEqual(i, r[i - 1]._internal['solution_id'])
            self.assertEqual('cat%s' % str(i), r[i - 1]._internal['catalog_id'])
            self.assertEqual('grp%s' % str(i), r[i - 1]._setup['group'])
            self.assertEqual('name%s' % str(i), r[i - 1]._setup['name'])
            self.assertEqual('version%s' % str(i), r[i - 1]._setup['version'])

    def test_get_all_installed_solutions_by_catalog(self):
        self.test_catalog_collection_index.insert_solution(
            "cat1", self._get_solution_attrs(1, "grp1", "name1", "version1")
        )
        self.test_catalog_collection_index.insert_solution(
            "cat2", self._get_solution_attrs(2, "grp2", "name2", "version2")
        )
        self.test_catalog_collection_index.insert_solution(
            "cat2", self._get_solution_attrs(3, "grp3", "name3", "version3")
        )
        self.test_catalog_collection_index.insert_solution(
            "cat2", self._get_solution_attrs(4, "grp4", "name4", "version4")
        )

        supp_attrs = ["installed", "installation_unfinished"]
        self.test_catalog_collection_index.update_solution(
            "cat2", Coordinates("grp2", "name2", "version2"), {"installed": 1, "installation_unfinished": 0}, supp_attrs
        )
        self.test_catalog_collection_index.update_solution(
            "cat2", Coordinates("grp4", "name4", "version4"), {"installed": 1, "installation_unfinished": 0}, supp_attrs
        )

        # call
        r1 = self.test_catalog_collection_index.get_all_installed_solutions_by_catalog("cat1")
        r2 = self.test_catalog_collection_index.get_all_installed_solutions_by_catalog("cat2")

        # assert
        expected = [
            self.test_catalog_collection_index.get_solution_by_collection_id(2),
            self.test_catalog_collection_index.get_solution_by_collection_id(4)
        ]

        self.assertEqual([], r1)
        self.assertListEqual(expected, r2)

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

        r = self.test_catalog_collection_index.get_solution_by_collection_id(3)

        expected = self._get_expected_attrs_setup({
            "catalog_id": "cat3",
            "group": "grp3",
            "name": "name3",
            "version": "version3"
        })

        self.assertEqual(3, r._internal['collection_id'])
        self.assertEqual(3, r._internal['solution_id'])
        self.assertDictEqual(expected, r._setup)

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

        self.assertEqual(1, r._internal['collection_id'])
        self.assertEqual(1, r._internal['solution_id'])
        self.assertEqual('catalog_id_exceptionell', r._internal['catalog_id'])
        self.assertEqual('grp_exceptionell', r._setup['group'])
        self.assertEqual('name_exceptionell', r._setup['name'])
        self.assertEqual('version_exceptionell', r._setup['version'])

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
            self.assertEqual(i, r[i - 1]._internal['collection_id'])
            self.assertEqual(i, r[i - 1]._internal['solution_id'])
            self.assertEqual('cat%s' % str(i), r[i - 1]._internal['catalog_id'])
            self.assertEqual('grp', r[i - 1]._setup['group'])
            self.assertEqual('name', r[i - 1]._setup['name'])
            self.assertEqual('version', r[i - 1]._setup['version'])

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

        supp_attrs = ["install_date", "installed"]
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
        self.assertEqual(3, len(r))
        self.assertEqual(inst_date1, r[0]._internal['install_date'])
        self.assertEqual(inst_date3, r[1]._internal['install_date'])
        self.assertEqual(inst_date2, r[2]._internal['install_date'])
        self.assertEqual(1, r[0]._internal['installed'])
        self.assertEqual(1, r[1]._internal['installed'])
        self.assertEqual(1, r[2]._internal['installed'])
        self.assertEqual(1, r[0]._internal['collection_id'])
        self.assertEqual(3, r[1]._internal['collection_id'])
        self.assertEqual(2, r[2]._internal['collection_id'])
        self.assertEqual(1, r[0]._internal['solution_id'])
        self.assertEqual(3, r[1]._internal['solution_id'])
        self.assertEqual(2, r[2]._internal['solution_id'])
        self.assertEqual(1, r[0]._internal['catalog_id'])
        self.assertEqual(1, r[1]._internal['catalog_id'])
        self.assertEqual(2, r[2]._internal['catalog_id'])
        self.assertEqual('grp', r[0]._setup['group'])
        self.assertEqual('grp_d', r[1]._setup['group'])
        self.assertEqual('grp', r[2]._setup['group'])
        self.assertEqual('name', r[0]._setup['name'])
        self.assertEqual('name_d', r[1]._setup['name'])
        self.assertEqual('name', r[2]._setup['name'])
        self.assertEqual('version', r[0]._setup['version'])
        self.assertEqual('version_d', r[1]._setup['version'])
        self.assertEqual('version', r[2]._setup['version'])

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

        supp_attrs = ["last_execution", "installed"]
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
        self.assertEqual(4, len(r))
        self.assertEqual(inst_date1, r[0]._internal['last_execution'])
        self.assertEqual(inst_date3, r[1]._internal['last_execution'])
        self.assertEqual(inst_date2, r[2]._internal['last_execution'])
        self.assertEqual(inst_date4, r[3]._internal['last_execution'])
        self.assertEqual(1, r[0]._internal['installed'])
        self.assertEqual(1, r[1]._internal['installed'])
        self.assertEqual(1, r[2]._internal['installed'])
        self.assertEqual(0, r[3]._internal['installed'])
        self.assertEqual(1, r[0]._internal['collection_id'])
        self.assertEqual(3, r[1]._internal['collection_id'])
        self.assertEqual(2, r[2]._internal['collection_id'])
        self.assertEqual(4, r[3]._internal['collection_id'])
        self.assertEqual(1, r[0]._internal['solution_id'])
        self.assertEqual(3, r[1]._internal['solution_id'])
        self.assertEqual(2, r[2]._internal['solution_id'])
        self.assertEqual(4, r[3]._internal['solution_id'])
        self.assertEqual(1, r[0]._internal['catalog_id'])
        self.assertEqual(1, r[1]._internal['catalog_id'])
        self.assertEqual(2, r[2]._internal['catalog_id'])
        self.assertEqual(1, r[3]._internal['catalog_id'])
        self.assertEqual('grp', r[0]._setup['group'])
        self.assertEqual('grp_d', r[1]._setup['group'])
        self.assertEqual('grp', r[2]._setup['group'])
        self.assertEqual('grp_u', r[3]._setup['group'])
        self.assertEqual('name', r[0]._setup['name'])
        self.assertEqual('name_d', r[1]._setup['name'])
        self.assertEqual('name', r[2]._setup['name'])
        self.assertEqual('name_u', r[3]._setup['name'])
        self.assertEqual('version', r[0]._setup['version'])
        self.assertEqual('version_d', r[1]._setup['version'])
        self.assertEqual('version', r[2]._setup['version'])
        self.assertEqual('version_u', r[3]._setup['version'])

    def test_get_unfinished_installation_solutions(self):
        self.assertEqual([], self.test_catalog_collection_index.get_all_solutions())
        self.test_catalog_collection_index.insert_solution("cat1",
                                                           self._get_solution_attrs(1, "grp", "name", "version"))
        s2 = self.test_catalog_collection_index.insert_solution("cat2",
                                                                self._get_solution_attrs(2, "grp", "name", "version"))
        self.test_catalog_collection_index.insert_solution("cat1",
                                                           self._get_solution_attrs(3, "grp_d", "name_d", "version_d"))

        self.assertEqual(3, len(self.test_catalog_collection_index.get_all_solutions()))

        self.test_catalog_collection_index.update_solution(
            "cat2", Coordinates("grp", "name", "version"), {"installation_unfinished": 1}, ["installation_unfinished"]
        )

        expected_collection_solution = self.test_catalog_collection_index.get_solution_by_collection_id(s2)

        # call
        r = self.test_catalog_collection_index.get_unfinished_installation_solutions()

        # assert
        self.assertEqual(1, len(r))
        self.assertEqual(expected_collection_solution._internal['solution_id'], r[0]._internal['solution_id'])
        self.assertEqual(expected_collection_solution, r[0])

    def test_update_solution(self):
        self.assertEqual([], self.test_catalog_collection_index.get_all_solutions())
        self.test_catalog_collection_index.insert_solution("cat1",
                                                           self._get_solution_attrs(1, "grp", "name", "version"))
        self.test_catalog_collection_index.insert_solution("cat2",
                                                           self._get_solution_attrs(2, "grp", "name", "version"))
        self.test_catalog_collection_index.insert_solution("cat1",
                                                           self._get_solution_attrs(3, "grp_d", "name_d", "version_d"))

        self.assertEqual(3, len(self.test_catalog_collection_index.get_all_solutions()))

        r = self.test_catalog_collection_index.get_solution_by_collection_id(2)
        self.assertIsNone(r._internal["last_execution"])

        # call
        self.test_catalog_collection_index.update_solution("cat2", Coordinates("grp", "name", "version"), {},
                                                           CatalogIndex.get_solution_column_keys())

        r = self.test_catalog_collection_index.get_solution_by_collection_id(2)
        self.assertIsNotNone(r._internal["last_execution"])

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

        supp_attrs = ["installed", "installation_unfinished"]
        self.test_catalog_collection_index.update_solution(
            "cat2", Coordinates("grp", "name", "version"), {"installed": 1, "installation_unfinished": 0}, supp_attrs
        )

        self.assertFalse(self.test_catalog_collection_index.is_installed("cat1", Coordinates("grp", "name", "version")))
        self.assertTrue(self.test_catalog_collection_index.is_installed("cat2", Coordinates("grp", "name", "version")))

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

    def _get_expected_attrs_internal(self, attrs):
        d = dict()
        d["collection_id"] = attrs["collection_id"]
        d["solution_id"] = attrs["solution_id"]
        d["catalog_id"] = attrs["catalog_id"]
        d["changelog"] = None
        d["last_execution"] = None
        d["parent"] = None
        d["children"] = []
        d["installed"] = 0
        return d

    def _get_expected_attrs_setup(self, attrs):
        d = self.get_solution_dict()
        d["group"] = attrs["group"]
        d["name"] = attrs["name"]
        d["version"] = attrs["version"]
        d["doi"] = attrs.get("doi", None)
        return d

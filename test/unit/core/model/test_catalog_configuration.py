import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import yaml

from hips.core.model.catalog_collection import HipsCatalogCollection
from test.unit.test_common import TestHipsCommon


class TestHipsCatalogCollection(TestHipsCommon):

    def setUp(self):
        self.config_file = Path(self.tmp_dir.name).joinpath("config_file")
        with open(self.config_file, "w+") as f:
            f.write(
                """catalogs: \n- %s\n- %s\n- %s""" %
                (
                    str(Path(self.tmp_dir.name).joinpath("catalogs", "test_catalog")),
                    str("https://gitlab.com/ida-mdc/hips-catalog.git"),
                    str(Path(self.tmp_dir.name).joinpath("catalogs", "test_catalog2"))
                )
            )
        HipsCatalogCollection.instance = None  # lever out concept
        self.config = HipsCatalogCollection(Path(self.tmp_dir.name).joinpath("config_file"))

    def test__init__(self):
        self.assertTrue(self.config_file.is_file())
        self.assertEqual(len(self.config.catalogs), 3)
        with open(self.config_file, "r") as f:
            self.assertEqual(self.config.config_file_dict, yaml.safe_load(f))
        self.assertEqual(self.config.local_catalog, self.config.catalogs[0])

    def test_get_default_deployment_catalog(self):
        self.config.catalogs[0].is_local = False
        c = self.config.get_default_deployment_catalog()
        self.assertEqual(c.id, "test_catalog")

    def test_get_default_deployment_catalog_no_catalog(self):
        for c in self.config.catalogs:
            c.is_local = True

        with self.assertRaises(LookupError):
            self.config.get_default_deployment_catalog()

    def test_get_catalog_by_url(self):
        self.config.catalogs[0].is_local = False
        self.config.catalogs[0].src = "myurl"
        c = self.config.get_catalog_by_url("myurl")
        self.assertEqual(c.id, "test_catalog")

    def test_get_catalog_by_url_local_error(self):
        self.config.catalogs[0].is_local = True
        self.config.catalogs[0].src = "myurl"

        with self.assertRaises(ValueError):
            self.config.get_catalog_by_url("myurl")

    def test_get_catalog_by_id(self):
        expected_id = self.config.catalogs[0].id

        self.assertEqual(expected_id, self.config.get_catalog_by_id(expected_id).id)

    def test_save(self):
        self.config.config_file_dict = {
            "catalogs": [str(Path(self.tmp_dir.name).joinpath("catalogs", "test_catalog_save"))]
        }
        self.config.save()
        with open(self.config_file, "r") as f:
            self.assertEqual(
                yaml.safe_load(f),
                yaml.safe_load(
                    "{'catalogs': ['%s']}" % str(Path(self.tmp_dir.name).joinpath("catalogs", "test_catalog_save")))
            )

    @patch('hips.core.model.catalog_collection.get_dict_from_yml', return_value={""})
    def test__load_hips_configuration(self, get_dict_mock):
        config_file_dict = self.config._load_hips_configuration()

        get_dict_mock.assert_called_once()

        self.assertEqual(config_file_dict, {""})

    @patch('hips.core.model.catalog_collection.get_dict_from_yml', return_value={})
    def test__load_hips_configuration_empty_file(self, get_dict_mock):

        with self.assertRaises(IOError):
            self.config._load_hips_configuration()

        get_dict_mock.assert_called_once()

    @patch('hips.core.model.catalog_collection.HipsCatalogCollection._create_default_configuration',
           return_value="Called")
    @patch('hips.core.model.catalog_collection.HipsCatalogCollection.save', return_value=None)
    def test__load_hips_configuration_no_file(self, save_mock, _create_default_mock):

        self.config.config_file_path = Path("doesNotExist")
        r = self.config._load_hips_configuration()

        _create_default_mock.assert_called_once()
        save_mock.assert_called_once_with("Called")

        self.assertEqual(r, "Called")

    @patch('hips.core.model.configuration.HipsConfiguration.get_default_hips_configuration', return_value="Called")
    def test__create_default_configuration(self, create_default_mock):

        r = self.config._create_default_configuration()

        create_default_mock.assert_called_once()

        self.assertEqual(r, "Called")

    def test__get_catalogs_no_catalogs(self):
        self.config.config_file_dict = {}

        with self.assertRaises(RuntimeError):
            self.config._get_catalogs()

    def test__get_catalogs(self):
        c = self.config._get_catalogs()

        self.assertEqual(len(c), 3)

    def test__get_local_catalog_no_catalog(self):
        for c in self.config.catalogs:
            c.is_local = False

        with self.assertRaises(RuntimeError):
            self.config._get_local_catalog()

    def test__get_local_catalog(self):
        r = self.config._get_local_catalog()

        self.assertEqual(r, self.config.catalogs[0])

    @patch('hips.core.model.catalog.Catalog.resolve_doi', return_value=None)
    @patch('hips.core.model.catalog.Catalog.resolve', return_value=None)
    def test_resolve_no_doi(self, catalog_resolve_mock, catalog_resolve_doi_mock):
        hips_attr = dict()
        hips_attr["group"] = "group"
        hips_attr["name"] = "name"
        hips_attr["version"] = "version"

        r = self.config.resolve(hips_attr)

        self.assertIsNone(r)
        self.assertEqual(3, catalog_resolve_mock.call_count)
        catalog_resolve_doi_mock.assert_not_called()

    @patch('hips.core.model.catalog.Catalog.resolve_doi', return_value=None)
    @patch('hips.core.model.catalog.Catalog.resolve', return_value=None)
    def test_resolve_with_doi(self, catalog_resolve_mock, catalog_resolve_doi_mock):
        hips_attr = dict()
        hips_attr["group"] = "group"
        hips_attr["name"] = "name"
        hips_attr["version"] = "version"
        hips_attr["doi"] = "aNiceDoi"

        r = self.config.resolve(hips_attr)

        self.assertIsNone(r)
        self.assertEqual(3, catalog_resolve_doi_mock.call_count)
        catalog_resolve_mock.assert_not_called()

    @patch('hips.core.model.catalog.Catalog.resolve_doi', return_value=None)
    @patch('hips.core.model.catalog.Catalog.resolve', return_value="pathToSolutionFile")
    def test_resolve_found_first_catalog(self, catalog_resolve_mock, catalog_resolve_doi_mock):
        hips_attr = dict()
        hips_attr["group"] = "group"
        hips_attr["name"] = "name"
        hips_attr["version"] = "version"

        r = self.config.resolve(hips_attr)

        self.assertEqual({"path": "pathToSolutionFile", "catalog": self.config.catalogs[0]}, r)
        self.assertEqual(1, catalog_resolve_mock.call_count)
        catalog_resolve_doi_mock.assert_not_called()

    def test_resolve_hips_dependency_raise_error(self):

        # mocks
        resolve_mock = MagicMock(return_value=None)
        self.config.resolve = resolve_mock

        with self.assertRaises(ValueError):
            r = self.config.resolve_hips_dependency(dict())
            self.assertIsNone(r)

        resolve_mock.assert_called_once()

    def test_resolve_hips_dependency_found(self):
        # mocks
        resolve_mock = MagicMock(return_value={"something"})
        self.config.resolve = resolve_mock

        r = self.config.resolve_hips_dependency(dict())

        self.assertEqual({"something"}, r)
        resolve_mock.assert_called_once()

    def test_resolve_from_str_valid_file(self):
        # mocks
        get_doi_from_input = MagicMock(return_value=None)
        get_gnv_from_input = MagicMock(return_value=None)
        resolve_hips_dependency = MagicMock(return_value=None)

        self.config.get_doi_from_input = get_doi_from_input
        self.config.get_doi_from_input = get_gnv_from_input
        self.config.get_doi_from_input = resolve_hips_dependency

        with tempfile.NamedTemporaryFile() as f:
            r = self.config.resolve_from_str(f.name)

            self.assertEqual({"path": Path(f.name), "catalog": None}, r)

        get_doi_from_input.assert_not_called()
        get_gnv_from_input.assert_not_called()
        resolve_hips_dependency.assert_not_called()

    def test_resolve_from_str_wrong_input(self):
        # mocks
        get_doi_from_input = MagicMock(return_value=None)
        get_gnv_from_input = MagicMock(return_value=None)
        resolve_hips_dependency = MagicMock(return_value=None)

        self.config.get_doi_from_input = get_doi_from_input
        self.config.get_gnv_from_input = get_gnv_from_input
        self.config.resolve_hips_dependency = resolve_hips_dependency

        with self.assertRaises(ValueError):
            self.config.resolve_from_str("aVeryStupidInput")

        get_doi_from_input.assert_called_once()
        get_gnv_from_input.assert_called_once()
        resolve_hips_dependency.assert_not_called()

    def test_resolve_from_str_doi_input(self):
        # mocks
        get_doi_from_input = MagicMock(return_value="doi")
        get_gnv_from_input = MagicMock(return_value=None)
        resolve_hips_dependency = MagicMock(return_value="solvedDoi")

        self.config.get_doi_from_input = get_doi_from_input
        self.config.get_gnv_from_input = get_gnv_from_input
        self.config.resolve_hips_dependency = resolve_hips_dependency

        r = self.config.resolve_from_str("doi_input")

        self.assertEqual("solvedDoi", r)
        get_doi_from_input.assert_called_once()
        get_gnv_from_input.assert_not_called()
        resolve_hips_dependency.assert_called_once_with("doi", True)

    def test_resolve_from_str_gnv_input(self):
        # mocks
        get_doi_from_input = MagicMock(return_value=None)
        get_gnv_from_input = MagicMock(return_value="gnv")
        resolve_hips_dependency = MagicMock(return_value="solvedGnv")

        self.config.get_doi_from_input = get_doi_from_input
        self.config.get_gnv_from_input = get_gnv_from_input
        self.config.resolve_hips_dependency = resolve_hips_dependency

        r = self.config.resolve_from_str("gnv_input")

        self.assertEqual("solvedGnv", r)

        get_doi_from_input.assert_called_once()
        get_gnv_from_input.assert_called_once()
        resolve_hips_dependency.assert_called_once_with("gnv", True)

    def test_get_gnv_from_input(self):
        solution = {
            "group": "grp",
            "name": "name",
            "version": "version"
        }

        self.assertEqual(solution, self.config.get_gnv_from_input("grp:name:version"))
        self.assertIsNone(self.config.get_gnv_from_input("grp:name"))
        self.assertIsNone(self.config.get_gnv_from_input("grp:version"))
        self.assertIsNone(self.config.get_gnv_from_input("grp:name:version:uselessInput"))
        self.assertIsNone(self.config.get_gnv_from_input("uselessInput"))
        self.assertIsNone(self.config.get_gnv_from_input("::"))
        self.assertIsNone(self.config.get_gnv_from_input("doi:prefix/suffix"))

    def test_get_doi_from_input(self):
        solution = {
            "doi": "prefix/suffix",
        }
        self.assertEqual(solution, self.config.get_doi_from_input("doi:prefix/suffix"))
        self.assertEqual(solution, self.config.get_doi_from_input("prefix/suffix"))
        self.assertIsNone(self.config.get_doi_from_input("prefixOnly"))
        self.assertIsNone(self.config.get_doi_from_input("doi:"))
        self.assertIsNone(self.config.get_doi_from_input(":"))
        self.assertIsNone(self.config.get_doi_from_input("grp:name:version"))

    def test_get_search_index(self):
        # mock
        get_leaves_dict_list = MagicMock(return_value=["someLeafs"])
        for c in self.config.catalogs:
            c.catalog_index.get_leaves_dict_list = get_leaves_dict_list

        r = self.config.get_search_index()

        self.assertEqual({
            "test_catalog": ["someLeafs"],
            "hips-catalog": ["someLeafs"],
            "test_catalog2": ["someLeafs"],
        }, r)

        self.assertEqual(3, get_leaves_dict_list.call_count)

    def test_get_installed_solutions(self):
        # mock
        list_installed = MagicMock(return_value=["someInstalledSolutions"])
        for c in self.config.catalogs:
            c.list_installed = list_installed

        r = self.config.get_installed_solutions()

        self.assertEqual({
            "test_catalog": ["someInstalledSolutions"],
            "hips-catalog": ["someInstalledSolutions"],
            "test_catalog2": ["someInstalledSolutions"],
        }, r)

        self.assertEqual(3, list_installed.call_count)


if __name__ == '__main__':
    unittest.main()

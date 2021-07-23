import unittest
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import yaml

from album.core.model.catalog_collection import CatalogCollection
from album.core.model.configuration import Configuration
from album.core.model.default_values import DefaultValues
from test.unit.test_unit_common import TestUnitCommon


class TestCatalogCollection(TestUnitCommon):

    def setUp(self):
        super().setUp()
        self.config_file = Path(self.tmp_dir.name).joinpath("config_file")
        with open(self.config_file, "w+") as f:
            f.write(
                """catalogs: \n- %s\n- %s\n- %s""" %
                (
                    str(Path(self.tmp_dir.name).joinpath("catalogs", "test_catalog")),
                    str(DefaultValues.catalog_url.value),
                    str(Path(self.tmp_dir.name).joinpath("catalogs", "test_catalog2"))
                )
            )

        config = Configuration()
        config.setup(
            base_cache_path=self.tmp_dir.name,
            configuration_file_path=Path(self.tmp_dir.name).joinpath("config_file")
        )
        self.test_catalog_collection = CatalogCollection()

    def test__init__(self):
        self.assertTrue(self.config_file.is_file())
        self.assertEqual(len(self.test_catalog_collection.catalogs), 3)
        with open(self.config_file, "r") as f:
            self.assertEqual(self.test_catalog_collection.config_file_dict, yaml.safe_load(f))
        self.assertEqual(self.test_catalog_collection.local_catalog, self.test_catalog_collection.catalogs[0])

    def test_get_default_deployment_catalog(self):
        self.test_catalog_collection.catalogs[0].is_local = False
        c = self.test_catalog_collection.get_default_deployment_catalog()
        self.assertEqual(c.id, "test_catalog")

    def test_get_default_deployment_catalog_no_catalog(self):
        for c in self.test_catalog_collection.catalogs:
            c.is_local = True

        with self.assertRaises(LookupError):
            self.test_catalog_collection.get_default_deployment_catalog()

    def test_get_catalog_by_url(self):
        self.test_catalog_collection.catalogs[0].is_local = False
        self.test_catalog_collection.catalogs[0].src = "myurl"
        c = self.test_catalog_collection.get_catalog_by_url("myurl")
        self.assertEqual(c.id, "test_catalog")

    def test_get_catalog_by_url_local_error(self):
        self.test_catalog_collection.catalogs[0].is_local = True
        self.test_catalog_collection.catalogs[0].src = "myurl"

        with self.assertRaises(LookupError):
            self.test_catalog_collection.get_catalog_by_url("myurl")

    def test_get_catalog_by_id(self):
        expected_id = self.test_catalog_collection.catalogs[0].id

        self.assertEqual(expected_id, self.test_catalog_collection.get_catalog_by_id(expected_id).id)

    def test_save(self):
        self.test_catalog_collection.config_file_dict = {
            "catalogs": [str(Path(self.tmp_dir.name).joinpath("catalogs", "test_catalog_save"))]
        }
        self.test_catalog_collection.save()
        with open(self.config_file, "r") as f:
            self.assertEqual(
                yaml.safe_load(f),
                yaml.safe_load(
                    "{'catalogs': ['%s']}" % str(Path(self.tmp_dir.name).joinpath("catalogs", "test_catalog_save")))
            )

    @patch('album.core.model.catalog_collection.get_dict_from_yml', return_value={""})
    def test__load_configuration(self, get_dict_mock):
        config_file_dict = self.test_catalog_collection._load_configuration()

        get_dict_mock.assert_called_once()

        self.assertEqual(config_file_dict, {""})

    @patch('album.core.model.catalog_collection.get_dict_from_yml', return_value={})
    def test__load_configuration_empty_file(self, get_dict_mock):

        with self.assertRaises(IOError):
            self.test_catalog_collection._load_configuration()

        get_dict_mock.assert_called_once()

    @patch('album.core.model.catalog_collection.CatalogCollection._create_default_configuration',
           return_value="Called")
    @patch('album.core.model.catalog_collection.CatalogCollection.save', return_value=None)
    def test__load_configuration_no_file(self, save_mock, _create_default_mock):

        self.test_catalog_collection.config_file_path = Path("doesNotExist")
        r = self.test_catalog_collection._load_configuration()

        _create_default_mock.assert_called_once()
        save_mock.assert_called_once_with("Called")

        self.assertEqual(r, "Called")

    @patch('album.core.model.configuration.Configuration.get_default_configuration', return_value="Called")
    def test__create_default_configuration(self, create_default_mock):

        r = self.test_catalog_collection._create_default_configuration()

        create_default_mock.assert_called_once()

        self.assertEqual(r, "Called")

    def test__get_catalogs_no_catalogs(self):
        self.test_catalog_collection.config_file_dict = {}

        with self.assertRaises(RuntimeError):
            self.test_catalog_collection._get_catalogs()

    def test__get_catalogs(self):
        c = self.test_catalog_collection._get_catalogs()

        self.assertEqual(len(c), 3)

    def test__get_local_catalog_no_catalog(self):
        for c in self.test_catalog_collection.catalogs:
            c.is_local = False

        with self.assertRaises(RuntimeError):
            self.test_catalog_collection._get_local_catalog()

    def test__get_local_catalog(self):
        r = self.test_catalog_collection._get_local_catalog()

        self.assertEqual(r, self.test_catalog_collection.catalogs[0])

    @patch('album.core.model.catalog.Catalog.refresh_index')
    def test_resolve(self, refresh_index_mock):
        # mocks
        _resolve_in_catalog = MagicMock(return_value=None)
        self.test_catalog_collection._resolve_in_catalog = _resolve_in_catalog

        solution_attr = dict()

        r = self.test_catalog_collection.resolve(solution_attr, update=False)

        self.assertIsNone(r)
        self.assertEqual(3, _resolve_in_catalog.call_count)
        refresh_index_mock.assert_not_called()

    @patch('album.core.model.catalog.Catalog.refresh_index')
    def test_resolve_update(self, refresh_index_mock):
        # mocks
        refresh_index_mock.return_value = None

        _resolve_in_catalog = MagicMock(return_value=None)
        self.test_catalog_collection._resolve_in_catalog = _resolve_in_catalog

        solution_attr = dict()

        r = self.test_catalog_collection.resolve(solution_attr, update=True)

        self.assertIsNone(r)
        self.assertEqual(3, _resolve_in_catalog.call_count)
        refresh_index_mock.assert_called_once()

    def test_resolve_found_locally(self):
        # mocks
        _resolve_in_catalog = MagicMock(return_value="aPath")
        self.test_catalog_collection._resolve_in_catalog = _resolve_in_catalog

        solution_attr = dict()

        r = self.test_catalog_collection.resolve(solution_attr, update=False)

        _resolve_in_catalog.assert_called_once_with(self.test_catalog_collection.local_catalog, solution_attr)

        self.assertDictEqual(
            {
                "path": "aPath",
                "catalog": self.test_catalog_collection.local_catalog
            },
            r
        )

    def test_resolve_locally_not_found(self):
        # mocks
        _resolve_in_catalog = MagicMock()
        _resolve_in_catalog.side_effect = [None, "path"]
        self.test_catalog_collection._resolve_in_catalog = _resolve_in_catalog

        solution_attr = dict()

        r = self.test_catalog_collection.resolve(solution_attr, update=False)

        self.assertEqual(r, {
            "path": "path",
            "catalog": self.test_catalog_collection.catalogs[1]
        })
        self.assertEqual(2, _resolve_in_catalog.call_count)

    @patch('album.core.model.catalog.Catalog.resolve_doi', return_value=None)
    @patch('album.core.model.catalog.Catalog.resolve', return_value=None)
    def test__resolve_in_catalog_no_doi_no_group(self, catalog_resolve_mock, catalog_resolve_doi_mock):
        solution_attr = dict()
        solution_attr["name"] = "name"
        solution_attr["version"] = "version"

        with self.assertRaises(ValueError):
            self.test_catalog_collection._resolve_in_catalog(self.test_catalog_collection.local_catalog, solution_attr)

        catalog_resolve_mock.assert_not_called()
        catalog_resolve_doi_mock.assert_not_called()

    @patch('album.core.model.catalog.Catalog.resolve_doi', return_value=None)
    @patch('album.core.model.catalog.Catalog.resolve', return_value=None)
    def test__resolve_in_catalog_with_doi(self, catalog_resolve_mock, catalog_resolve_doi_mock):
        solution_attr = dict()
        solution_attr["group"] = "group"
        solution_attr["name"] = "name"
        solution_attr["version"] = "version"
        solution_attr["doi"] = "aNiceDoi"

        with self.assertRaises(NotImplementedError):
            self.test_catalog_collection._resolve_in_catalog(self.test_catalog_collection.local_catalog, solution_attr)

    @patch('album.core.model.catalog.Catalog.resolve_doi', return_value=None)
    @patch('album.core.model.catalog.Catalog.resolve', return_value="pathToSolutionFile")
    def test__resolve_in_catalog_found_first_catalog(self, catalog_resolve_mock, catalog_resolve_doi_mock):
        solution_attr = dict()
        solution_attr["group"] = "group"
        solution_attr["name"] = "name"
        solution_attr["version"] = "version"

        r = self.test_catalog_collection._resolve_in_catalog(self.test_catalog_collection.catalogs[0], solution_attr)

        self.assertEqual("pathToSolutionFile", r)
        catalog_resolve_mock.assert_called_once()
        catalog_resolve_doi_mock.assert_not_called()

    def test_resolve_dependency_raise_error(self):

        # mocks
        resolve_mock = MagicMock(return_value=None)
        self.test_catalog_collection.resolve = resolve_mock

        with self.assertRaises(ValueError):
            r = self.test_catalog_collection.resolve_dependency(dict())
            self.assertIsNone(r)

        resolve_mock.assert_called_once()

    def test_resolve_dependency_found(self):
        # mocks
        resolve_mock = MagicMock(return_value={"something"})
        self.test_catalog_collection.resolve = resolve_mock

        r = self.test_catalog_collection.resolve_dependency(dict())

        self.assertEqual({"something"}, r)
        resolve_mock.assert_called_once()

    def test_get_search_index(self):
        # mock
        get_leaves_dict_list = MagicMock(return_value=["someLeafs"])
        for c in self.test_catalog_collection.catalogs:
            c.catalog_index.get_leaves_dict_list = get_leaves_dict_list

        r = self.test_catalog_collection.get_search_index()

        self.assertEqual({
            "test_catalog": ["someLeafs"],
            "default": ["someLeafs"],
            "test_catalog2": ["someLeafs"],
        }, r)

        self.assertEqual(3, get_leaves_dict_list.call_count)


if __name__ == '__main__':
    unittest.main()

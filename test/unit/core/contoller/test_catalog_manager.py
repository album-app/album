import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import yaml

from album.core.controller.catalog_manager import CatalogManager
from album.core.model.configuration import Configuration
from album.core.model.default_values import DefaultValues
from test.unit.test_unit_common import TestUnitCommon


class TestCatalogManager(TestUnitCommon):

    def setUp(self):
        super().setUp()
        self.config_file = Path(self.tmp_dir.name).joinpath("config_file")
        self.catalog_list = [
            str(Path(self.tmp_dir.name).joinpath("catalogs", "test_catalog")),
            str(DefaultValues.catalog_url.value),
            str(Path(self.tmp_dir.name).joinpath("catalogs", "test_catalog2"))
        ]

        with open(self.config_file, "w+") as f:
            f.write("""catalogs: \n- %s\n- %s\n- %s""" % tuple(self.catalog_list))

        config = Configuration()
        config.setup(
            base_cache_path=self.tmp_dir.name,
            configuration_file_path=Path(self.tmp_dir.name).joinpath("config_file")
        )
        self.test_catalog_manager = CatalogManager()

    def test__init__(self):
        self.assertTrue(self.config_file.is_file())
        self.assertEqual(len(self.test_catalog_manager.catalogs), 3)
        with open(self.config_file, "r") as f:
            self.assertEqual(self.test_catalog_manager.config_file_dict, yaml.safe_load(f))
        self.assertEqual(self.test_catalog_manager.local_catalog, self.test_catalog_manager.catalogs[0])

    def test_get_default_deployment_catalog(self):
        self.test_catalog_manager.catalogs[0].is_local = False
        c = self.test_catalog_manager.get_default_deployment_catalog()
        self.assertEqual(c.id, "test_catalog")

    def test_get_default_deployment_catalog_no_catalog(self):
        for c in self.test_catalog_manager.catalogs:
            c.is_local = True

        with self.assertRaises(LookupError):
            self.test_catalog_manager.get_default_deployment_catalog()

    def test_get_catalog_by_url(self):
        self.test_catalog_manager.catalogs[0].is_local = False
        self.test_catalog_manager.catalogs[0].src = "myurl"
        c = self.test_catalog_manager.get_catalog_by_url("myurl")
        self.assertEqual(c.id, "test_catalog")

    def test_get_catalog_by_url_local_error(self):
        self.test_catalog_manager.catalogs[0].is_local = True
        self.test_catalog_manager.catalogs[0].src = "myurl"

        with self.assertRaises(LookupError):
            self.test_catalog_manager.get_catalog_by_url("myurl")

    def test_get_catalog_by_id(self):
        expected_id = self.test_catalog_manager.catalogs[0].id

        self.assertEqual(expected_id, self.test_catalog_manager.get_catalog_by_id(expected_id).id)

    def test_get_catalog_by_id_not_configured(self):
        with self.assertRaises(LookupError):
            self.test_catalog_manager.get_catalog_by_id("aFaultyId")

    def test_extract_catalog_name(self):
        catalog_name = "https://gitlab.com/album-app/capture-knowledge.ext"

        self.assertEqual(self.test_catalog_manager.extract_catalog_name(catalog_name), "capture-knowledge")

    def test_save(self):
        self.test_catalog_manager.config_file_dict = {
            "catalogs": [str(Path(self.tmp_dir.name).joinpath("catalogs", "test_catalog_save"))]
        }
        self.test_catalog_manager.save()
        with open(self.config_file, "r") as f:
            self.assertEqual(
                yaml.safe_load(f),
                yaml.safe_load(
                    "{'catalogs': ['%s']}" % str(Path(self.tmp_dir.name).joinpath("catalogs", "test_catalog_save")))
            )

    @patch('album.core.controller.catalog_manager.get_dict_from_yml', return_value={""})
    def test__load_configuration(self, get_dict_mock):
        config_file_dict = self.test_catalog_manager._load_configuration()

        get_dict_mock.assert_called_once()

        self.assertEqual(config_file_dict, {""})

    @patch('album.core.controller.catalog_manager.get_dict_from_yml', return_value={})
    def test__load_configuration_empty_file(self, get_dict_mock):

        with self.assertRaises(IOError):
            self.test_catalog_manager._load_configuration()

        get_dict_mock.assert_called_once()

    def test__load_configuration_no_file(self):
        # mocks
        save_mock = MagicMock(return_value=None)
        self.test_catalog_manager.save = save_mock

        get_default_configuration = MagicMock(return_value="Called")
        self.test_catalog_manager.configuration.get_default_configuration = get_default_configuration

        self.test_catalog_manager.config_file_path = Path("doesNotExist")
        r = self.test_catalog_manager._load_configuration()

        get_default_configuration.assert_called_once()
        save_mock.assert_called_once_with("Called")

        self.assertEqual(r, "Called")

    def test__get_catalogs_no_catalogs(self):
        self.test_catalog_manager.config_file_dict = {}

        with self.assertRaises(RuntimeError):
            self.test_catalog_manager._get_catalogs()

    def test__get_catalogs(self):
        c = self.test_catalog_manager._get_catalogs()

        self.assertEqual(len(c), 3)

        self.assertFalse(c[0].is_deletable)
        self.assertFalse(c[1].is_deletable)
        self.assertTrue(c[2].is_deletable)

    def test__get_local_catalog_no_catalog(self):
        for c in self.test_catalog_manager.catalogs:
            c.is_local = False

        with self.assertRaises(RuntimeError):
            self.test_catalog_manager._get_local_catalog()

    def test__get_local_catalog(self):
        r = self.test_catalog_manager._get_local_catalog()

        self.assertEqual(r, self.test_catalog_manager.catalogs[0])

    @patch('album.core.model.catalog.Catalog.refresh_index')
    def test_resolve(self, refresh_index_mock):
        # mocks
        _resolve_in_catalog = MagicMock(return_value=None)
        self.test_catalog_manager._resolve_in_catalog = _resolve_in_catalog

        solution_attr = dict()

        # call
        r = self.test_catalog_manager.resolve(solution_attr)

        self.assertIsNone(r)
        self.assertEqual(3, _resolve_in_catalog.call_count)
        refresh_index_mock.assert_not_called()

    def test_resolve_found_locally(self):
        # mocks
        _resolve_in_catalog = MagicMock(return_value="aPath")
        self.test_catalog_manager._resolve_in_catalog = _resolve_in_catalog

        solution_attr = dict()

        # call
        r = self.test_catalog_manager.resolve(solution_attr)

        _resolve_in_catalog.assert_called_once_with(self.test_catalog_manager.local_catalog, solution_attr)

        self.assertDictEqual(
            {
                "path": "aPath",
                "catalog": self.test_catalog_manager.local_catalog
            },
            r
        )

    def test_resolve_locally_not_found(self):
        # mocks
        _resolve_in_catalog = MagicMock()
        _resolve_in_catalog.side_effect = [None, "path"]
        self.test_catalog_manager._resolve_in_catalog = _resolve_in_catalog

        solution_attr = dict()

        r = self.test_catalog_manager.resolve(solution_attr)

        self.assertEqual(r, {
            "path": "path",
            "catalog": self.test_catalog_manager.catalogs[1]
        })
        self.assertEqual(2, _resolve_in_catalog.call_count)

    @patch('album.core.model.catalog.Catalog.resolve_doi', return_value=None)
    @patch('album.core.model.catalog.Catalog.resolve', return_value=None)
    def test__resolve_in_catalog_no_doi_no_group(self, catalog_resolve_mock, catalog_resolve_doi_mock):
        solution_attr = dict()
        solution_attr["name"] = "name"
        solution_attr["version"] = "version"

        with self.assertRaises(ValueError):
            self.test_catalog_manager._resolve_in_catalog(self.test_catalog_manager.local_catalog, solution_attr)

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
            self.test_catalog_manager._resolve_in_catalog(self.test_catalog_manager.local_catalog, solution_attr)

    @patch('album.core.model.catalog.Catalog.resolve_doi', return_value=None)
    @patch('album.core.model.catalog.Catalog.resolve', return_value="pathToSolutionFile")
    def test__resolve_in_catalog_found_first_catalog(self, catalog_resolve_mock, catalog_resolve_doi_mock):
        solution_attr = dict()
        solution_attr["group"] = "group"
        solution_attr["name"] = "name"
        solution_attr["version"] = "version"

        r = self.test_catalog_manager._resolve_in_catalog(self.test_catalog_manager.catalogs[0], solution_attr)

        self.assertEqual("pathToSolutionFile", r)
        catalog_resolve_mock.assert_called_once()
        catalog_resolve_doi_mock.assert_not_called()

    def test_resolve_dependency_raise_error(self):

        # mocks
        resolve_mock = MagicMock(return_value=None)
        self.test_catalog_manager.resolve = resolve_mock

        with self.assertRaises(ValueError):
            r = self.test_catalog_manager.resolve_dependency(dict())
            self.assertIsNone(r)

        resolve_mock.assert_called_once()

    def test_resolve_dependency_found(self):
        # mocks
        resolve_mock = MagicMock(return_value={"something"})
        self.test_catalog_manager.resolve = resolve_mock

        r = self.test_catalog_manager.resolve_dependency(dict())

        self.assertEqual({"something"}, r)
        resolve_mock.assert_called_once()

    def test_get_search_index(self):
        # mock
        get_leaves_dict_list = MagicMock(return_value=["someLeafs"])
        for c in self.test_catalog_manager.catalogs:
            c.catalog_index.get_leaves_dict_list = get_leaves_dict_list

        r = self.test_catalog_manager.get_search_index()

        self.assertEqual({
            "test_catalog": ["someLeafs"],
            "default": ["someLeafs"],
            "test_catalog2": ["someLeafs"],
        }, r)

        self.assertEqual(3, get_leaves_dict_list.call_count)

    def test__check_requirement(self):
        self.assertIsNone(self.test_catalog_manager._check_requirement(self.solution_default_dict))
        sol_dict = deepcopy(self.solution_default_dict)
        sol_dict.pop("version")
        with self.assertRaises(ValueError):
            self.assertTrue(self.test_catalog_manager._check_requirement(sol_dict))

    def test_resolve_directly_not_found(self):
        # mocks
        resolve = MagicMock(return_value=None)

        for c in self.test_catalog_manager.catalogs:
            c.resolve = resolve

        # call
        r = self.test_catalog_manager.resolve_directly(self.test_catalog_manager.local_catalog.id, "g", "n", "v")

        # check
        self.assertIsNone(r)
        # assert
        resolve.assert_called_once_with("g", "n", "v")

    def test_resolve_directly(self):
        # mocks
        expected = {"path": "aPathToTheSolution", "catalog": self.test_catalog_manager.local_catalog}
        resolve = MagicMock(return_value="aPathToTheSolution")

        for c in self.test_catalog_manager.catalogs:
            c.resolve = resolve

        # call
        r = self.test_catalog_manager.resolve_directly(self.test_catalog_manager.local_catalog.id, "g", "n", "v")

        # check
        self.assertEqual(expected, r)
        # assert
        resolve.assert_called_once_with("g", "n", "v")

    def test_remove_by_id(self):
        # mocks
        save = MagicMock()
        self.test_catalog_manager.save = save

        reload = MagicMock()
        self.test_catalog_manager.reload = reload

        # call
        self.test_catalog_manager.remove_by_id(self.test_catalog_manager.catalogs[2].id)

        # assert
        expected_list = deepcopy(self.catalog_list)
        expected_list.pop(2)

        self.assertEqual({"catalogs": expected_list}, self.test_catalog_manager.config_file_dict)

        save.assert_called_once()
        reload.assert_called_once()

    def test_remove_by_id_url(self):
        # mocks
        save = MagicMock()
        self.test_catalog_manager.save = save

        reload = MagicMock()
        self.test_catalog_manager.reload = reload

        self.test_catalog_manager.catalogs[1].is_deletable = True

        # call
        self.test_catalog_manager.remove_by_id(self.test_catalog_manager.catalogs[1].id)

        # assert
        expected_list = deepcopy(self.catalog_list)
        expected_list.pop(1)

        self.assertEqual({"catalogs": expected_list}, self.test_catalog_manager.config_file_dict)

        save.assert_called_once()
        reload.assert_called_once()

    def test_remove_by_id_undeletable(self):
        # mocks
        save = MagicMock()
        self.test_catalog_manager.save = save

        reload = MagicMock()
        self.test_catalog_manager.reload = reload

        # call
        x = self.test_catalog_manager.remove_by_id(self.test_catalog_manager.catalogs[0].id)

        # assert
        self.assertIsNone(x)
        self.assertEqual({"catalogs": self.catalog_list}, self.test_catalog_manager.config_file_dict)  # nothing changed

        save.assert_not_called()
        reload.assert_not_called()

    def test_remove_by_id_invalid_id(self):
        # mocks
        save = MagicMock()
        self.test_catalog_manager.save = save

        reload = MagicMock()
        self.test_catalog_manager.reload = reload

        # call
        with self.assertRaises(LookupError):
            self.test_catalog_manager.remove_by_id("aWrongIdOfACatalogToRemove")

        # assert
        self.assertEqual({"catalogs": self.catalog_list}, self.test_catalog_manager.config_file_dict)  # nothing changed
        save.assert_not_called()
        reload.assert_not_called()

    def test_remove(self):
        # mock
        remove_by_id = MagicMock()
        self.test_catalog_manager.remove_by_id = remove_by_id

        # call
        self.test_catalog_manager.remove(self.catalog_list[0])

        # assert
        remove_by_id.assert_called_once_with(self.test_catalog_manager.catalogs[0].id)

    def test_remove_not_configured(self):
        # mocks
        remove_by_id = MagicMock()
        self.test_catalog_manager.remove_by_id = remove_by_id

        # call
        self.test_catalog_manager.remove("wrongPath")

        # assert
        remove_by_id.assert_not_called()

    def test_add(self):
        # mocks
        save = MagicMock()
        self.test_catalog_manager.save = save

        reload = MagicMock()
        self.test_catalog_manager.reload = reload

        # call
        self.test_catalog_manager.add("aNiceCatalog")

        # assert
        expected_list = deepcopy(self.catalog_list)
        expected_list.append("aNiceCatalog")
        self.assertEqual({"catalogs": expected_list}, self.test_catalog_manager.config_file_dict)

        save.assert_called_once()
        reload.assert_called_once()

    def test_update_any_no_id(self):
        # mocks
        update_all = MagicMock(return_value=None)
        self.test_catalog_manager.update_all = update_all
        update_by_id = MagicMock(return_value=None)
        self.test_catalog_manager.update_by_id = update_by_id

        # call
        self.test_catalog_manager.update_any()
        update_all.assert_called_once()
        update_by_id.assert_not_called()

    def test_update_any(self):
        # mocks
        update_all = MagicMock(return_value=None)
        self.test_catalog_manager.update_all = update_all
        update_by_id = MagicMock(return_value=None)
        self.test_catalog_manager.update_by_id = update_by_id

        # call
        self.test_catalog_manager.update_any("aNiceCatalogID")
        update_all.assert_not_called()
        update_by_id.assert_called_once()

    def test_update_all(self):
        # mocks
        _update = MagicMock(return_value=True)
        self.test_catalog_manager._update = _update

        # call
        r = self.test_catalog_manager.update_all()

        self.assertEqual(3, _update.call_count)
        self.assertEqual([True, True, True], r)

    def test_update_all_failed(self):
        # mocks
        _update = MagicMock()
        _update.side_effect = [True, ConnectionError(), True]
        self.test_catalog_manager._update = _update

        # call
        r = self.test_catalog_manager.update_all()

        # assert
        self.assertEqual(3, _update.call_count)
        self.assertEqual([True, False, True], r)

    def test_update_by_id(self):
        # mocks
        _update = MagicMock(return_value=True)
        self.test_catalog_manager._update = _update

        get_catalog_by_id = MagicMock(return_value="myCatalog")
        self.test_catalog_manager.get_catalog_by_id = get_catalog_by_id

        # call
        self.test_catalog_manager.update_by_id("aNiceId")

        # assert
        get_catalog_by_id.assert_called_once_with("aNiceId")
        _update.assert_called_once_with("myCatalog")

    def test__update(self):
        # mocks
        refresh_index = MagicMock(return_value=True)
        self.test_catalog_manager.local_catalog.refresh_index = refresh_index

        # call
        r = self.test_catalog_manager._update(self.test_catalog_manager.local_catalog)

        # assert
        self.assertTrue(r)
        refresh_index.assert_called_once()


if __name__ == '__main__':
    unittest.main()

import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from album.core import AlbumClass
from album.core.controller.catalog_manager import CatalogManager
from album.core.model.catalog import Catalog
from album.core.model.default_values import DefaultValues
from test.unit.test_unit_common import TestUnitCommon, EmptyTestClass


class TestCatalogManager(TestUnitCommon):

    def setUp(self):
        super().setUp()
        self.create_test_config()
        test_catalog1_name = "test_catalog"
        test_catalog1_src = Path(self.tmp_dir.name).joinpath("my-catalogs", test_catalog1_name)
        test_catalog2_name = "test_catalog2"
        test_catalog2_src = Path(self.tmp_dir.name).joinpath("my-catalogs", "test_catalog2")
        test_catalog1_src.mkdir(parents=True)
        test_catalog2_src.mkdir(parents=True)
        with open(test_catalog1_src.joinpath(DefaultValues.catalog_index_file_json.value), 'w') as file:
            file.writelines("{\"name\": \"" + test_catalog1_name + "\", \"version\": \"0.1.0\"}")

        with open(test_catalog2_src.joinpath(DefaultValues.catalog_index_file_json.value), 'w') as file:
            file.writelines("{\"name\": \"" + test_catalog2_name + "\", \"version\": \"0.1.0\"}")

        self.catalog_list = [
            {
                'catalog_id': 1,
                'deletable': 0,
                'name': test_catalog1_name,
                'path': str(Path(self.tmp_dir.name).joinpath(DefaultValues.catalog_folder_prefix.value, test_catalog1_name)),
                'src': str(test_catalog1_src)
            },
            {
                'catalog_id': 2,
                'deletable': 1,
                'name': "default",
                'path': str(Path(self.tmp_dir.name).joinpath(DefaultValues.catalog_folder_prefix.value, "default")),
                'src': str(DefaultValues.default_catalog_src.value)
            },
            {
                'catalog_id': 3,
                'deletable': 1,
                'name': test_catalog2_name,
                'path': str(Path(self.tmp_dir.name).joinpath(DefaultValues.catalog_folder_prefix.value, "test_catalog2")),
                'src': str(test_catalog2_src)
            }
        ]
        with patch("album.core.controller.catalog_manager.CatalogManager.add_initial_catalogs") as add_initial_catalogs_mock:
            self.test_catalog_manager = CatalogManager()

        for catalog in self.catalog_list:
            self.test_catalog_manager.catalog_collection.insert_catalog(
                catalog["name"],
                catalog["src"],
                catalog["path"],
                catalog["deletable"]
            )
        self.assertEqual(self.catalog_list, self.test_catalog_manager.catalog_collection.get_all_catalogs())

        self.create_test_solution_no_env()

    def test_get_catalog_by_src(self):
        c = self.test_catalog_manager.get_catalog_by_src(str(DefaultValues.default_catalog_src.value))
        self.assertEqual(c.name, "default")

    def test_get_catalog_by_name(self):
        expected_name = self.test_catalog_manager.get_catalogs()[0].name

        self.assertEqual(expected_name, self.test_catalog_manager.get_catalog_by_name(expected_name).name)

    def test_get_catalog_by_name_not_configured(self):
        with self.assertRaises(LookupError):
            self.test_catalog_manager.get_catalog_by_name("aFaultyId")

    def test_get_catalog_by_path(self):
        c = self.test_catalog_manager.get_catalog_by_path(self.catalog_list[0]['path'])
        self.assertEqual(c.name, self.catalog_list[0]['name'])

    def test__get_catalogs(self):
        c = self.test_catalog_manager.get_catalogs()

        self.assertEqual(len(c), 3)

        self.assertFalse(c[0].is_deletable)
        self.assertTrue(c[1].is_deletable)
        self.assertTrue(c[2].is_deletable)

    @unittest.skip("Needs to be implemented")
    def test__get_catalogs_no_catalogs(self):
        pass

    def test__get_local_catalog(self):
        r = self.test_catalog_manager.get_local_catalog()

        local_catalog = self.test_catalog_manager.get_catalogs()[0]
        self.assertEqual(r.catalog_id, local_catalog.catalog_id)
        self.assertEqual(r.name, local_catalog.name)
        self.assertEqual(r.src, local_catalog.src)

    @unittest.skip("Needs to be implemented")
    def test__get_local_catalog_no_catalog(self):
        pass

    @patch('album.core.model.catalog.Catalog.refresh_index')
    def test_resolve_in_catalogs(self, refresh_index_mock):
        # mocks
        _resolve_in_catalog = MagicMock(return_value=None)
        self.test_catalog_manager._resolve_in_catalog = _resolve_in_catalog

        solution_attr = dict()

        # call
        r = self.test_catalog_manager.resolve_in_catalogs(solution_attr)

        self.assertIsNone(r)
        self.assertEqual(3, _resolve_in_catalog.call_count)
        refresh_index_mock.assert_not_called()

    def test_resolve_found_locally(self):
        # mocks
        _resolve_in_catalog = MagicMock(return_value="aPath")
        self.test_catalog_manager._resolve_in_catalog = _resolve_in_catalog

        solution_attr = dict()

        # call
        r = self.test_catalog_manager.resolve_in_catalogs(solution_attr)

        _resolve_in_catalog.assert_called_once()

        self.assertEqual("aPath", r["path"])
        self.assertEqual(self.test_catalog_manager.get_local_catalog().catalog_id, r["catalog"].catalog_id)

    def test_resolve_locally_not_found(self):
        # mocks
        _resolve_in_catalog = MagicMock()
        _resolve_in_catalog.side_effect = [None, "path"]
        self.test_catalog_manager._resolve_in_catalog = _resolve_in_catalog

        solution_attr = dict()

        r = self.test_catalog_manager.resolve_in_catalogs(solution_attr)

        self.assertEqual(r["path"], "path")
        catalog1 = self.test_catalog_manager.get_catalogs()[1]
        self.assertEqual(r["catalog"].name, catalog1.name)
        self.assertEqual(r["catalog"].src, catalog1.src)
        self.assertEqual(r["catalog"].path, catalog1.path)
        self.assertEqual(2, _resolve_in_catalog.call_count)

    def test__resolve_in_catalog_no_doi_no_group(self):
        # mocks
        resolve_mock = MagicMock(return_value=None)
        resolve_doi_mock = MagicMock(return_value=None)
        self.test_catalog_manager.resolve = resolve_mock
        self.test_catalog_manager.resolve_doi = resolve_doi_mock


        solution_attr = dict()
        solution_attr["name"] = "name"
        solution_attr["version"] = "version"

        with self.assertRaises(ValueError):
            self.test_catalog_manager._resolve_in_catalog(self.test_catalog_manager.get_local_catalog(), solution_attr)

        resolve_mock.assert_not_called()
        resolve_doi_mock.assert_not_called()

    def test__resolve_in_catalog_with_doi(self):
        # mocks
        resolve_mock = MagicMock(return_value=None)
        resolve_doi_mock = MagicMock(return_value=None)
        self.test_catalog_manager.resolve = resolve_mock
        self.test_catalog_manager.resolve_doi = resolve_doi_mock

        solution_attr = dict()
        solution_attr["group"] = "group"
        solution_attr["name"] = "name"
        solution_attr["version"] = "version"
        solution_attr["doi"] = "aNiceDoi"

        with self.assertRaises(NotImplementedError):
            self.test_catalog_manager._resolve_in_catalog(self.test_catalog_manager.get_local_catalog(), solution_attr)

    def test__resolve_in_catalog_found_first_catalog(self):
        # mocks
        resolve_mock = MagicMock(return_value="pathToSolutionFile")
        resolve_doi_mock = MagicMock(return_value=None)
        self.test_catalog_manager.resolve = resolve_mock
        self.test_catalog_manager.resolve_doi = resolve_doi_mock

        solution_attr = dict()
        solution_attr["group"] = "group"
        solution_attr["name"] = "name"
        solution_attr["version"] = "version"

        r = self.test_catalog_manager._resolve_in_catalog(self.test_catalog_manager.get_catalogs()[0], solution_attr)

        self.assertEqual("pathToSolutionFile", r)
        resolve_mock.assert_called_once()
        resolve_doi_mock.assert_not_called()

    def test__update(self):
        # mocks
        refresh_index = MagicMock(return_value=True)
        local_catalog = self.test_catalog_manager.get_local_catalog()
        local_catalog.refresh_index = refresh_index

        # call
        r = self.test_catalog_manager._update(local_catalog)

        # assert
        self.assertTrue(r)
        refresh_index.assert_called_once()

    def test_update_by_name(self):
        # mocks
        _update = MagicMock(return_value=True)
        self.test_catalog_manager._update = _update

        get_catalog_by_id = MagicMock(return_value="myCatalog")
        self.test_catalog_manager.get_catalog_by_name = get_catalog_by_id

        # call
        self.test_catalog_manager.update_by_name("aNiceName")

        # assert
        get_catalog_by_id.assert_called_once_with("aNiceName")
        _update.assert_called_once_with("myCatalog")

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

    def test_update_any(self):
        # mocks
        update_all = MagicMock(return_value=None)
        self.test_catalog_manager.update_all = update_all
        update_by_name = MagicMock(return_value=None)
        self.test_catalog_manager.update_by_name = update_by_name

        # call
        self.test_catalog_manager.update_any("aNiceCatalogID")
        update_all.assert_not_called()
        update_by_name.assert_called_once()

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

    def test_add(self):
        catalog_name = "aNiceCatalog"
        catalog_src = Path(self.tmp_dir.name).joinpath("my-catalogs", catalog_name)
        catalog_src.mkdir(parents=True)
        with open(catalog_src.joinpath(DefaultValues.catalog_index_file_json.value), 'w') as config:
            config.writelines("{\"name\": \"" + catalog_name + "\", \"version\": \"0.1.0\"}")

        # call
        self.test_catalog_manager.add_catalog_to_collection(catalog_src)

        # assert
        expected_list = deepcopy(self.catalog_list)
        expected_list.append({
            "catalog_id": 4,
            "deletable": 1,
            "name": catalog_name,
            "path": str(Path(self.tmp_dir.name).joinpath(DefaultValues.catalog_folder_prefix.value, catalog_name)),
            "src": str(catalog_src),
        })
        self.assertEqual(expected_list, self.test_catalog_manager.catalog_collection.get_all_catalogs())

    def test_remove_catalog_from_collection(self):
        # mock
        remove_by_name = MagicMock()
        self.test_catalog_manager.remove_catalog_from_collection_by_name = remove_by_name

        # call
        self.test_catalog_manager.remove_catalog_from_collection_by_name(self.catalog_list[0]['name'])

        # assert
        remove_by_name.assert_called_once_with(self.test_catalog_manager.catalog_collection.get_all_catalogs()[0]['name'])

    def test_remove_catalog_from_collection_not_configured(self):
        # mocks
        remove_by_id = MagicMock()
        self.test_catalog_manager._remove_by_name = remove_by_id

        # call
        self.test_catalog_manager.remove_catalog_from_collection_by_path("wrongPath")

        # assert
        remove_by_id.assert_not_called()

    def test__remove_by_path(self):
        # mock
        remove_by_path = MagicMock()
        self.test_catalog_manager.remove_catalog_from_collection_by_path = remove_by_path

        # call
        self.test_catalog_manager.remove_catalog_from_collection_by_path(self.catalog_list[0]['path'])

        # assert
        remove_by_path.assert_called_once_with(self.test_catalog_manager.catalog_collection.get_all_catalogs()[0]['path'])

    def test__remove_by_name(self):
        # call
        catalogs = self.test_catalog_manager.catalog_collection.get_all_catalogs()
        self.test_catalog_manager.remove_catalog_from_collection_by_name(catalogs[2]["name"])

        # assert
        expected_list = deepcopy(self.catalog_list)
        expected_list.pop(2)

        catalogs = self.test_catalog_manager.catalog_collection.get_all_catalogs()
        self.assertEqual(expected_list, catalogs)

    def test__remove_by_name_url(self):
        self.test_catalog_manager.remove_catalog_from_collection_by_name(self.test_catalog_manager.get_catalogs()[1].name)

        # assert
        expected_list = deepcopy(self.catalog_list)
        expected_list.pop(1)

        self.assertEqual(expected_list, self.test_catalog_manager.catalog_collection.get_all_catalogs())

    def test__remove_by_name_undeletable(self):
        # call
        catalogs = self.test_catalog_manager.catalog_collection.get_all_catalogs()
        x = self.test_catalog_manager.remove_catalog_from_collection_by_name(catalogs[0]['name'])

        # assert
        self.assertIsNone(x)
        self.assertEqual(self.catalog_list, self.test_catalog_manager.catalog_collection.get_all_catalogs())  # nothing changed

    def test__remove_by_name_invalid_name(self):
        # call
        with self.assertRaises(LookupError):
            self.test_catalog_manager.remove_catalog_from_collection_by_name("aWrongIdOfACatalogToRemove")

        # assert
        self.assertEqual(self.catalog_list, self.test_catalog_manager.catalog_collection.get_all_catalogs())  # nothing changed

    def test_remove_by_src(self):
        # mock
        remove_by_src = MagicMock()
        self.test_catalog_manager.remove_catalog_from_collection_by_src = remove_by_src

        # call
        self.test_catalog_manager.remove_catalog_from_collection_by_src(self.catalog_list[0]['src'])

        # assert
        remove_by_src.assert_called_once_with(
            self.test_catalog_manager.catalog_collection.get_all_catalogs()[0]['src'])

    @patch('album.core.utils.operations.resolve_operations.load')
    @patch('album.core.controller.catalog_manager.Catalog.get_solution_file')
    def test_resolve_dependency_and_load(self, get_solution_file_mock, load_mock):
        # mocks
        load_mock.return_value = self.active_solution

        get_solutions_by_grp_name_version = MagicMock(return_value=[{"catalog_id": "aNiceId", "installed": True, "group": "g", "name": "n", "version": "v"}])
        self.test_catalog_manager.catalog_collection.get_solutions_by_grp_name_version = get_solutions_by_grp_name_version
        get_catalog_by_id_mock = MagicMock(return_value=Catalog("aNiceId", "aNiceName", "aValidPath"))
        self.test_catalog_manager.get_catalog_by_id = get_catalog_by_id_mock

        _catalog = EmptyTestClass()
        _catalog.catalog_id = "aNiceId"
        _catalog.name = "aNiceName"

        get_solution_file_mock.return_value = "aValidPath"

        set_environment = MagicMock(return_value=None)
        self.active_solution.set_environment = set_environment

        # call
        r = self.test_catalog_manager.resolve_dependency_and_load({"group": "g", "name": "n", "version": "v"})

        self.assertEqual(get_solution_file_mock.return_value, r[0]["path"])
        self.assertEqual(self.active_solution, r[1])

        get_solutions_by_grp_name_version.assert_called_once_with("g", "n", "v")
        get_solution_file_mock.assert_called_once_with("g", "n", "v")
        load_mock.assert_called_once_with("aValidPath")
        set_environment.assert_called_once_with(_catalog.name)
        get_catalog_by_id_mock.assert_called_once_with("aNiceId")

    @patch('album.core.utils.operations.resolve_operations.load')
    def test_resolve_dependency_and_load_error(self, load_mock):
        # mocks
        load_mock.return_value = self.active_solution

        get_solutions_by_grp_name_version = MagicMock(return_value=None)
        self.test_catalog_manager.catalog_collection.get_solutions_by_grp_name_version = get_solutions_by_grp_name_version

        _catalog = EmptyTestClass()
        _catalog.id = "aNiceId"

        resolve_directly = MagicMock(return_value=None)
        self.test_catalog_manager.resolve_in_catalog = resolve_directly

        set_environment = MagicMock(return_value=None)
        self.active_solution.set_environment = set_environment

        # call
        with self.assertRaises(LookupError):
            self.test_catalog_manager.resolve_dependency_and_load({"group": "g", "name": "n", "version": "v"})

        get_solutions_by_grp_name_version.assert_called_once_with("g", "n", "v")
        resolve_directly.assert_not_called()
        load_mock.assert_not_called()
        set_environment.assert_not_called()

    @unittest.skip("Needs to be implemented!")
    def test_resolve_require_installation_and_load_valid_path(self):
        pass

    @patch('album.core.controller.catalog_manager._check_file_or_url')
    @patch('album.core.controller.catalog_manager.load')
    def test_resolve_require_installation_and_load_grp_name_version(self, load_mock, _check_file_or_url_mock):
        # mocks
        search_mock = MagicMock(return_value={"catalog_id": 1, "group": "grp", "name": "name", "version": "version", "installed": True})
        self.test_catalog_manager.search = search_mock
        load_mock.return_value = AlbumClass({"group": "grp", "name": "name", "version": "version"})
        _check_file_or_url_mock.return_value = None

        # call
        self.test_catalog_manager.resolve_require_installation_and_load("grp:name:version")

        # assert
        _check_file_or_url_mock.assert_called_once_with("grp:name:version", self.test_catalog_manager.tmp_cache_dir)

    @patch('album.core.controller.catalog_manager.copy_folder', return_value=None)
    @patch('album.core.controller.catalog_manager.clean_resolve_tmp', return_value=None)
    def test_add_to_local_catalog(self, clean_resolve_tmp, copy_folder_mock):
        # run
        self.active_solution.script = ""  # the script gets read during load()
        self.test_catalog_manager.add_to_local_catalog(self.active_solution, "aPathToInstall")

        # assert
        path = self.test_catalog_manager.get_local_catalog().get_solution_path(self.active_solution["group"], self.active_solution["name"], self.active_solution["version"])
        copy_folder_mock.assert_called_once_with("aPathToInstall", path, copy_root_folder=False)
        clean_resolve_tmp.assert_called_once()

    @unittest.skip("Needs to be implemented!")
    def test_resolve_download_and_load(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test__resolve(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_search_local_file(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_search(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test__search_in_local_catalog(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test__search_in_specific_catalog(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test__search_in_catalogs(self):
        pass


if __name__ == '__main__':
    unittest.main()

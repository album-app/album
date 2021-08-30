import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock, call
from unittest.mock import patch

from album.core import AlbumClass
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.model.catalog import Catalog
from album.core.model.catalog_updates import CatalogUpdates
from album.core.model.default_values import DefaultValues
from album.core.model.group_name_version import GroupNameVersion
from album.core.utils.operations.resolve_operations import dict_to_group_name_version
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
        with patch("album.core.controller.collection.collection_manager.CatalogHandler.add_initial_catalogs") as add_initial_catalogs_mock:
            self.collection_manager = CollectionManager()

        for catalog in self.catalog_list:
            self.collection_manager.catalog_collection.insert_catalog(
                catalog["name"],
                catalog["src"],
                catalog["path"],
                catalog["deletable"]
            )
        self.assertEqual(self.catalog_list, self.collection_manager.catalog_collection.get_all_catalogs())

        self.create_test_solution_no_env()

    def test_get_catalog_by_src(self):
        c = self.collection_manager.catalogs().get_by_src(str(DefaultValues.default_catalog_src.value))
        self.assertEqual(c.name, "default")

    def test_get_catalog_by_name(self):
        expected_name = self.collection_manager.catalogs().get_all()[0].name

        self.assertEqual(expected_name, self.collection_manager.catalogs().get_by_name(expected_name).name)

    def test_get_catalog_by_name_not_configured(self):
        with self.assertRaises(LookupError):
            self.collection_manager.catalogs().get_by_name("aFaultyId")

    def test_get_catalog_by_path(self):
        c = self.collection_manager.catalogs().get_by_path(self.catalog_list[0]['path'])
        self.assertEqual(c.name, self.catalog_list[0]['name'])

    def test__get_catalogs(self):
        c = self.collection_manager.catalogs().get_all()

        self.assertEqual(len(c), 3)

        self.assertFalse(c[0].is_deletable)
        self.assertTrue(c[1].is_deletable)
        self.assertTrue(c[2].is_deletable)

    @unittest.skip("Needs to be implemented")
    def test__get_catalogs_no_catalogs(self):
        pass

    def test__get_local_catalog(self):
        r = self.collection_manager.catalogs().get_local_catalog()

        local_catalog = self.collection_manager.catalogs().get_all()[0]
        self.assertEqual(r.catalog_id, local_catalog.catalog_id)
        self.assertEqual(r.name, local_catalog.name)
        self.assertEqual(r.src, local_catalog.src)

    @unittest.skip("Needs to be implemented")
    def test__get_local_catalog_no_catalog(self):
        pass

    def test__update(self):
        # mocks
        refresh_index = MagicMock(return_value=True)
        local_catalog = self.collection_manager.catalogs().get_local_catalog()
        local_catalog.refresh_index = refresh_index

        # call
        r = self.collection_manager.catalogs()._update(local_catalog)

        # assert
        self.assertTrue(r)
        refresh_index.assert_called_once()

    def test_update_by_name(self):
        # mocks
        _update = MagicMock(return_value=True)
        self.collection_manager.catalogs()._update = _update

        get_catalog_by_id = MagicMock(return_value="myCatalog")
        self.collection_manager.catalogs().get_by_name = get_catalog_by_id

        # call
        self.collection_manager.catalogs().update_by_name("aNiceName")

        # assert
        get_catalog_by_id.assert_called_once_with("aNiceName")
        _update.assert_called_once_with("myCatalog")

    def test_update_all(self):
        # mocks
        _update = MagicMock(return_value=True)
        self.collection_manager.catalogs()._update = _update

        # call
        r = self.collection_manager.catalogs().update_all()

        self.assertEqual(3, _update.call_count)
        self.assertEqual([True, True, True], r)

    def test_update_all_failed(self):
        # mocks
        _update = MagicMock()
        _update.side_effect = [True, ConnectionError(), True]
        self.collection_manager.catalogs()._update = _update

        # call
        r = self.collection_manager.catalogs().update_all()

        # assert
        self.assertEqual(3, _update.call_count)
        self.assertEqual([True, False, True], r)

    def test_update_any(self):
        # mocks
        update_all = MagicMock(return_value=None)
        self.collection_manager.catalogs().update_all = update_all
        update_by_name = MagicMock(return_value=None)
        self.collection_manager.catalogs().update_by_name = update_by_name

        # call
        self.collection_manager.catalogs().update_any("aNiceCatalogID")
        update_all.assert_not_called()
        update_by_name.assert_called_once()

    def test_update_any_no_id(self):
        # mocks
        update_all = MagicMock(return_value=None)
        self.collection_manager.catalogs().update_all = update_all
        update_by_id = MagicMock(return_value=None)
        self.collection_manager.update_by_id = update_by_id

        # call
        self.collection_manager.catalogs().update_any()
        update_all.assert_called_once()
        update_by_id.assert_not_called()

    def test_update_collection_dry_run(self):
        # mocks
        catalog = self.collection_manager.catalogs().get_local_catalog()
        _get_divergence_between_catalog_and_collection = MagicMock(return_value=CatalogUpdates(catalog))
        _update_collection_from_catalog = MagicMock(return_value=None)
        self.collection_manager.catalogs()._get_divergence_between_catalog_and_collection = _get_divergence_between_catalog_and_collection
        self.collection_manager.catalogs()._update_collection_from_catalog = _update_collection_from_catalog

        # call
        res = self.collection_manager.catalogs().update_collection(dry_run=True)

        # assert
        self.assertEqual(3, len(res))
        self.assertEqual(3, _get_divergence_between_catalog_and_collection.call_count)
        self.assertEqual([call(catalog_name=catalog.name), call(catalog_name='default'), call(catalog_name='test_catalog2')],
                         _get_divergence_between_catalog_and_collection.call_args_list)
        _update_collection_from_catalog.assert_not_called()

    def test_update_collection(self):
        # mocks
        catalog = self.collection_manager.catalogs().get_local_catalog()
        _update_collection_from_catalog = MagicMock(return_value=CatalogUpdates(catalog))
        self.collection_manager.catalogs()._update_collection_from_catalog = _update_collection_from_catalog

        # call
        res = self.collection_manager.catalogs().update_collection()

        # assert
        self.assertEqual(3, len(res))
        self.assertEqual(3, _update_collection_from_catalog.call_count)
        self.assertEqual([call(catalog_name=catalog.name), call(catalog_name='default'), call(catalog_name='test_catalog2')],
                         _update_collection_from_catalog.call_args_list)

    def test_update_collection_specific_catalog(self):
        # mocks
        catalog = self.collection_manager.catalogs().get_local_catalog()
        _update_collection_from_catalog = MagicMock(return_value=CatalogUpdates(catalog))
        self.collection_manager.catalogs()._update_collection_from_catalog = _update_collection_from_catalog

        # call
        res = self.collection_manager.catalogs().update_collection(catalog_name=catalog.name)

        # assert
        self.assertEqual(1, len(res))
        _update_collection_from_catalog.assert_called_once_with(catalog.name)

    def test_update_collection_specific_catalog_dry_run(self):
        # mocks
        catalog = self.collection_manager.catalogs().get_local_catalog()
        _get_divergence_between_catalog_and_collection = MagicMock(return_value=CatalogUpdates(catalog))
        _update_collection_from_catalog = MagicMock(return_value=CatalogUpdates(catalog))
        self.collection_manager.catalogs()._get_divergence_between_catalog_and_collection = _get_divergence_between_catalog_and_collection
        self.collection_manager.catalogs()._update_collection_from_catalog = _update_collection_from_catalog

        # call
        res = self.collection_manager.catalogs().update_collection(catalog_name=catalog.name, dry_run=True)

        # assert
        self.assertEqual(1, len(res))
        _get_divergence_between_catalog_and_collection.assert_called_once_with(catalog.name)
        _update_collection_from_catalog.assert_not_called()

    def test_add(self):
        catalog_name = "aNiceCatalog"
        catalog_src = Path(self.tmp_dir.name).joinpath("my-catalogs", catalog_name)
        catalog_src.mkdir(parents=True)
        with open(catalog_src.joinpath(DefaultValues.catalog_index_file_json.value), 'w') as config:
            config.writelines("{\"name\": \"" + catalog_name + "\", \"version\": \"0.1.0\"}")

        # call
        self.collection_manager.catalogs().add_by_src(catalog_src)

        # assert
        expected_list = deepcopy(self.catalog_list)
        expected_list.append({
            "catalog_id": 4,
            "deletable": 1,
            "name": catalog_name,
            "path": str(Path(self.tmp_dir.name).joinpath(DefaultValues.catalog_folder_prefix.value, catalog_name)),
            "src": str(catalog_src),
        })
        self.assertEqual(expected_list, self.collection_manager.catalog_collection.get_all_catalogs())

    def test_remove_catalog_from_collection(self):
        # mock
        remove_by_name = MagicMock()
        self.collection_manager.catalogs().remove_from_index_by_name = remove_by_name

        # call
        self.collection_manager.catalogs().remove_from_index_by_name(self.catalog_list[0]['name'])

        # assert
        remove_by_name.assert_called_once_with(self.collection_manager.catalog_collection.get_all_catalogs()[0]['name'])

    def test_remove_catalog_from_collection_not_configured(self):
        # mocks
        remove_by_id = MagicMock()
        self.collection_manager._remove_by_name = remove_by_id

        # call
        self.collection_manager.catalogs().remove_from_index_by_path("wrongPath")

        # assert
        remove_by_id.assert_not_called()

    def test__remove_by_path(self):
        # mock
        remove_by_path = MagicMock()
        self.collection_manager.catalogs().remove_from_index_by_path = remove_by_path

        # call
        self.collection_manager.catalogs().remove_from_index_by_path(self.catalog_list[0]['path'])

        # assert
        remove_by_path.assert_called_once_with(self.collection_manager.catalog_collection.get_all_catalogs()[0]['path'])

    def test__remove_by_name(self):
        # call
        catalogs = self.collection_manager.catalog_collection.get_all_catalogs()
        self.collection_manager.catalogs().remove_from_index_by_name(catalogs[2]["name"])

        # assert
        expected_list = deepcopy(self.catalog_list)
        expected_list.pop(2)

        catalogs = self.collection_manager.catalog_collection.get_all_catalogs()
        self.assertEqual(expected_list, catalogs)

    def test__remove_by_name_url(self):
        self.collection_manager.catalogs().remove_from_index_by_name(self.collection_manager.catalogs().get_all()[1].name)

        # assert
        expected_list = deepcopy(self.catalog_list)
        expected_list.pop(1)

        self.assertEqual(expected_list, self.collection_manager.catalog_collection.get_all_catalogs())

    def test__remove_by_name_undeletable(self):
        # call
        catalogs = self.collection_manager.catalog_collection.get_all_catalogs()
        x = self.collection_manager.catalogs().remove_from_index_by_name(catalogs[0]['name'])

        # assert
        self.assertIsNone(x)
        self.assertEqual(self.catalog_list, self.collection_manager.catalog_collection.get_all_catalogs())  # nothing changed

    def test__remove_by_name_invalid_name(self):
        # call
        with self.assertRaises(LookupError):
            self.collection_manager.catalogs().remove_from_index_by_name("aWrongIdOfACatalogToRemove")

        # assert
        self.assertEqual(self.catalog_list, self.collection_manager.catalog_collection.get_all_catalogs())  # nothing changed

    def test_remove_by_src(self):
        # mock
        remove_by_src = MagicMock()
        self.collection_manager.remove_catalog_from_collection_by_src = remove_by_src

        # call
        self.collection_manager.remove_catalog_from_collection_by_src(self.catalog_list[0]['src'])

        # assert
        remove_by_src.assert_called_once_with(
            self.collection_manager.catalog_collection.get_all_catalogs()[0]['src'])

    @patch('album.core.utils.operations.resolve_operations.load')
    @patch('album.core.controller.collection.catalog_handler.Catalog.get_solution_file')
    def test_resolve_dependency_and_load(self, get_solution_file_mock, load_mock):
        # mocks
        load_mock.return_value = self.active_solution

        get_solutions_by_grp_name_version = MagicMock(return_value=[{"catalog_id": "aNiceId", "installed": True, "group": "g", "name": "n", "version": "v"}])
        self.collection_manager.catalog_collection.get_solutions_by_grp_name_version = get_solutions_by_grp_name_version
        get_catalog_by_id_mock = MagicMock(return_value=Catalog("aNiceId", "aNiceName", "aValidPath"))
        self.collection_manager.catalogs().get_by_id = get_catalog_by_id_mock

        _catalog = EmptyTestClass()
        _catalog.catalog_id = "aNiceId"
        _catalog.name = "aNiceName"

        get_solution_file_mock.return_value = "aValidPath"

        set_environment = MagicMock(return_value=None)
        self.active_solution.set_environment = set_environment

        # call
        r = self.collection_manager.resolve_dependency_require_installation_and_load({"group": "g", "name": "n", "version": "v"})

        self.assertEqual(get_solution_file_mock.return_value, r.path)
        self.assertEqual(self.active_solution, r.active_solution)

        get_solutions_by_grp_name_version.assert_called_once_with(GroupNameVersion("g", "n", "v"))
        get_solution_file_mock.assert_called_once_with(GroupNameVersion("g", "n", "v"))
        load_mock.assert_called_once_with("aValidPath")
        set_environment.assert_called_once_with(_catalog.name)
        get_catalog_by_id_mock.assert_called_once_with("aNiceId")

    @patch('album.core.utils.operations.resolve_operations.load')
    def test_resolve_dependency_require_installation_and_load(self, load_mock):
        # mocks
        load_mock.return_value = self.active_solution

        get_solutions_by_grp_name_version = MagicMock(return_value=None)
        self.collection_manager.catalog_collection.get_solutions_by_grp_name_version = get_solutions_by_grp_name_version

        _catalog = EmptyTestClass()
        _catalog.id = "aNiceId"

        resolve_directly = MagicMock(return_value=None)
        self.collection_manager.resolve_in_catalog = resolve_directly

        set_environment = MagicMock(return_value=None)
        self.active_solution.set_environment = set_environment

        # call
        with self.assertRaises(LookupError):
            self.collection_manager.resolve_dependency_require_installation_and_load({"group": "g", "name": "n", "version": "v"})

        get_solutions_by_grp_name_version.assert_called_once_with(GroupNameVersion("g", "n", "v"))
        resolve_directly.assert_not_called()
        load_mock.assert_not_called()
        set_environment.assert_not_called()

    @unittest.skip("Needs to be implemented!")
    def test_resolve_require_installation_and_load_valid_path(self):
        pass

    @patch('album.core.controller.collection.collection_manager._check_file_or_url')
    @patch('album.core.controller.collection.collection_manager.load')
    def test_resolve_require_installation_and_load_grp_name_version(self, load_mock, _check_file_or_url_mock):
        # mocks
        search_mock = MagicMock(return_value={"catalog_id": 1, "group": "grp", "name": "name", "version": "version", "installed": True})
        self.collection_manager._search = search_mock
        load_mock.return_value = AlbumClass({"group": "grp", "name": "name", "version": "version"})
        _check_file_or_url_mock.return_value = None

        # call
        self.collection_manager.resolve_require_installation_and_load("grp:name:version")

        # assert
        _check_file_or_url_mock.assert_called_once_with("grp:name:version", self.collection_manager.tmp_cache_dir)

    @patch('album.core.controller.collection.solution_handler.copy_folder', return_value=None)
    @patch('album.core.controller.collection.collection_manager.clean_resolve_tmp', return_value=None)
    def test_add_to_local_catalog(self, clean_resolve_tmp, copy_folder_mock):
        # run
        self.active_solution.script = ""  # the script gets read during load()
        self.collection_manager.add_solution_to_local_catalog(self.active_solution, "aPathToInstall")

        # assert
        path = self.collection_manager.catalogs().get_local_catalog().get_solution_path(dict_to_group_name_version(self.solution_default_dict))
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

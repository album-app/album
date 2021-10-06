import unittest
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from album.core import Solution
from album.core.controller.collection.catalog_handler import CatalogHandler
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.controller.collection.solution_handler import SolutionHandler
from album.core.model.catalog import Catalog
from album.core.model.collection_index import CollectionIndex
from album.core.model.configuration import Configuration
from album.core.model.default_values import DefaultValues
from album.core.model.coordinates import Coordinates
from album.core.utils.operations.resolve_operations import dict_to_coordinates
from test.unit.test_unit_common import TestUnitCommon, EmptyTestClass


class TestCatalogCollectionCommon(TestUnitCommon):

    def setUp(self):
        super().setUp()
        self.create_test_config()

        test_catalog1_name = "test_catalog"
        test_catalog2_name = "test_catalog2"

        test_catalog1_src = self.create_empty_catalog(test_catalog1_name)
        test_catalog2_src = self.create_empty_catalog(test_catalog2_name)
        self.catalog_list = [
            {
                'catalog_id': 1,
                'deletable': 0,
                'name': test_catalog1_name,
                'path': str(
                    Path(self.tmp_dir.name).joinpath(DefaultValues.catalog_folder_prefix.value, test_catalog1_name)),
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
                'path': str(
                    Path(self.tmp_dir.name).joinpath(DefaultValues.catalog_folder_prefix.value, "test_catalog2")),
                'src': str(test_catalog2_src)
            }
        ]
        self.catalog_collection = CollectionIndex(
            DefaultValues.catalog_collection_name.value,
            Configuration().get_catalog_collection_path()
        )

    def tearDown(self) -> None:
        super().tearDown()

    def create_empty_catalog(self, name):
        catalog_path = Path(self.tmp_dir.name).joinpath("my-catalogs", name)
        catalog_path.mkdir(parents=True)
        with open(catalog_path.joinpath(DefaultValues.catalog_index_metafile_json.value), 'w') as file:
            file.writelines("{\"name\": \"" + name + "\", \"version\": \"0.1.0\"}")

        return catalog_path

    def fill_catalog_collection(self):
        # insert catalogs in DB from helper list
        for catalog in self.catalog_list:
            self.catalog_collection.insert_catalog(
                catalog["name"],
                catalog["src"],
                catalog["path"],
                catalog["deletable"]
            )
        self.assertEqual(self.catalog_list, self.catalog_collection.get_all_catalogs())


class TestCollectionManager(TestCatalogCollectionCommon):

    def setUp(self):
        super().setUp()
        self.fill_catalog_collection()

        # patch initial catalog creation
        with patch("album.core.controller.collection.collection_manager.CollectionManager._load_or_create_collection"):
            self.collection_manager = CollectionManager()

        # set test attributes
        self.collection_manager.catalog_collection = self.catalog_collection
        self.collection_manager.solution_handler = SolutionHandler(self.catalog_collection)
        self.collection_manager.catalog_handler = CatalogHandler(
            Configuration(),
            self.catalog_collection,
            self.collection_manager.solution_handler
        )

        self.create_test_solution_no_env()

    @unittest.skip("Needs to be implemented!")
    def test__load_or_create_collection(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_catalogs(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_solutions(self):
        # todo: implement
        pass

    @patch('album.core.controller.collection.solution_handler.copy_folder', return_value=None)
    @patch('album.core.controller.collection.collection_manager.clean_resolve_tmp', return_value=None)
    def test_add_to_local_catalog(self, clean_resolve_tmp, copy_folder_mock):
        # run
        self.active_solution.script = ""  # the script gets read during load()
        self.collection_manager.add_solution_to_local_catalog(self.active_solution, "aPathToInstall")

        # assert
        path = self.collection_manager.catalogs().get_local_catalog().get_solution_path(
            dict_to_coordinates(self.solution_default_dict))
        copy_folder_mock.assert_called_once_with("aPathToInstall", path, copy_root_folder=False)
        clean_resolve_tmp.assert_called_once()

    @unittest.skip("Needs to be implemented!")
    def get_index_as_dict(self):
        # todo: implement
        pass

    def test_remove_by_src(self):
        # mock
        remove_catalog_from_collection_by_src = MagicMock()
        self.collection_manager.remove_catalog_from_collection_by_src = remove_catalog_from_collection_by_src

        # call
        self.collection_manager.remove_catalog_from_collection_by_src(self.catalog_list[0]['src'])

        # assert
        remove_catalog_from_collection_by_src.assert_called_once_with(
            self.collection_manager.catalog_collection.get_all_catalogs()[0]['src'])

    @unittest.skip("Needs to be implemented!")
    def test_resolve_require_installation_and_load_valid_path(self):
        # todo: implement
        pass

    @patch('album.core.controller.collection.collection_manager._check_file_or_url')
    @patch('album.core.controller.collection.collection_manager.load')
    def test_resolve_require_installation_and_load_grp_name_version(self, load_mock, _check_file_or_url_mock):
        # mocks
        search_mock = MagicMock(
            return_value={"catalog_id": 1, "group": "grp", "name": "name", "version": "version", "installed": True})
        self.collection_manager._search = search_mock
        load_mock.return_value = Solution({"group": "grp", "name": "name", "version": "version"})
        _check_file_or_url_mock.return_value = None

        # call
        self.collection_manager.resolve_require_installation_and_load("grp:name:version")

        # assert
        _check_file_or_url_mock.assert_called_once_with("grp:name:version", self.collection_manager.tmp_cache_dir)

    @unittest.skip("Needs to be implemented!")
    def test_resolve_download_and_load(self):
        # todo: implement
        pass

    @patch('album.core.utils.operations.resolve_operations.load')
    @patch('album.core.controller.collection.catalog_handler.Catalog.get_solution_file')
    def test_resolve_dependency_require_installation_and_load(self, get_solution_file_mock, load_mock):
        # mocks
        load_mock.return_value = self.active_solution

        get_solutions_by_grp_name_version = MagicMock(
            return_value=[{"catalog_id": "aNiceId", "installed": True, "group": "g", "name": "n", "version": "v"}])
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
        r = self.collection_manager.resolve_dependency_require_installation_and_load(
            {"group": "g", "name": "n", "version": "v"})

        self.assertEqual(get_solution_file_mock.return_value, r.path)
        self.assertEqual(self.active_solution, r.active_solution)

        get_solutions_by_grp_name_version.assert_called_once_with(Coordinates("g", "n", "v"))
        get_solution_file_mock.assert_called_once_with(Coordinates("g", "n", "v"))
        load_mock.assert_called_once_with("aValidPath")
        set_environment.assert_called_once_with(_catalog.name)
        get_catalog_by_id_mock.assert_called_once_with("aNiceId")

    @patch('album.core.utils.operations.resolve_operations.load')
    def test_resolve_dependency_require_installation_and_load_error(self, load_mock):
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
            self.collection_manager.resolve_dependency_require_installation_and_load(
                {"group": "g", "name": "n", "version": "v"})

        get_solutions_by_grp_name_version.assert_called_once_with(Coordinates("g", "n", "v"))
        resolve_directly.assert_not_called()
        load_mock.assert_not_called()
        set_environment.assert_not_called()

    @unittest.skip("Needs to be implemented!")
    def test_resolve_dependency_require_installation(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_resolve_dependency(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__resolve(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__search_local_file(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__search(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__search_in_local_catalog(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__search_in_specific_catalog(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__search_in_catalogs(self):
        # todo: implement
        pass


if __name__ == '__main__':
    unittest.main()

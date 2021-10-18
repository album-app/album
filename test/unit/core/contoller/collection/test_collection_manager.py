import unittest
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from album.core.model.resolve_result import ResolveResult

from album.core import Solution
from album.core.controller.collection.catalog_handler import CatalogHandler
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.controller.collection.solution_handler import SolutionHandler
from album.core.model.catalog import Catalog
from album.core.model.collection_index import CollectionIndex
from album.core.model.configuration import Configuration
from album.core.model.coordinates import Coordinates
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.resolve_operations import dict_to_coordinates
from test.unit.test_unit_common import TestUnitCommon, EmptyTestClass


class TestCatalogCollectionCommon(TestUnitCommon):

    def setUp(self):
        super().setUp()
        self.create_album_test_instance()

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

    def test_catalogs(self):
        self.assertIsNotNone(self.collection_manager.catalogs())

    def test_solutions(self):
        self.assertIsNotNone(self.collection_manager.solutions())

    @patch('album.core.controller.collection.solution_handler.copy_folder', return_value=None)
    def test_add_to_local_catalog(self, copy_folder_mock):
        # run
        self.active_solution.script = ""  # the script gets read during load()
        self.collection_manager.add_solution_to_local_catalog(self.active_solution, "aPathToInstall")

        # assert
        path = self.collection_manager.catalogs().get_local_catalog().get_solution_path(
            dict_to_coordinates(self.solution_default_dict))
        copy_folder_mock.assert_called_once_with("aPathToInstall", path, copy_root_folder=False)

    def test_get_index_as_dict(self):
        expected_dict = {'catalogs': [
            {
                'catalog_id': 1,
                'name': 'test_catalog',
                'src': str(Path(self.tmp_dir.name).joinpath("my-catalogs", "test_catalog")),
                'path': str(Path(self.tmp_dir.name).joinpath("catalogs", "test_catalog")),
                'deletable': 0,
                'solutions': []
            }, {
                'catalog_id': 2,
                'name': 'default',
                'src': 'https://gitlab.com/album-app/catalogs/default',
                'path': str(Path(self.tmp_dir.name).joinpath("catalogs", "default")),
                'deletable': 1,
                'solutions': []
            },
            {
                'catalog_id': 3,
                'name': 'test_catalog2',
                'src': str(Path(self.tmp_dir.name).joinpath("my-catalogs", "test_catalog2")),
                'path': str(Path(self.tmp_dir.name).joinpath("catalogs", "test_catalog2")),
                'deletable': 1,
                'solutions': []
            }
        ]}
        self.assertEqual(expected_dict, self.collection_manager.get_index_as_dict())

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

    def test_resolve_download_and_load_catalog_coordinates(self):
        catalog = Catalog("aNiceId", "aNiceName", "aValidPath")
        coordinates = Coordinates("g", "n", "v")
        # mocks
        get_solution_mock = MagicMock(return_value="path/to/solution")
        search_mock = MagicMock(return_value={"group": "g", "name": "n", "version": "v"})
        retrieve_and_load_mock = MagicMock()
        self.collection_manager.solutions().get_solution_path_by_group_name_version = get_solution_mock
        self.collection_manager._search_in_specific_catalog = search_mock
        self.collection_manager._retrieve_and_load_resolve_result = retrieve_and_load_mock
        # call
        res = self.collection_manager.resolve_download_and_load_catalog_coordinates(catalog, coordinates)
        # assert
        self.assertEqual(catalog, res.catalog)
        self.assertEqual(get_solution_mock.return_value, res.path)
        self.assertEqual(search_mock.return_value, res.solution_attrs)
        get_solution_mock.assert_called_once_with(catalog, coordinates)
        search_mock.assert_called_once_with(catalog.catalog_id, coordinates)
        retrieve_and_load_mock.assert_called_once()

    def test_resolve_download_and_load_coordinates(self):
        coordinates = Coordinates("g", "n", "v")
        local_catalog = self.collection_manager.catalogs().get_local_catalog()
        # mocks
        get_catalog_mock = MagicMock(return_value=local_catalog)
        get_solution_mock = MagicMock(return_value="path/to/solution")
        search_mock = MagicMock(return_value={"catalog_id": 1})
        retrieve_and_load_mock = MagicMock()
        self.collection_manager._search_by_coordinates = search_mock
        self.collection_manager.catalogs().get_by_id = get_catalog_mock
        local_catalog.get_solution_file = get_solution_mock
        self.collection_manager._retrieve_and_load_resolve_result = retrieve_and_load_mock
        # call
        res = self.collection_manager.resolve_download_and_load_coordinates(coordinates)
        # assert
        self.assertEqual(local_catalog, res.catalog)
        self.assertEqual(get_solution_mock.return_value, res.path)
        self.assertEqual(search_mock.return_value, res.solution_attrs)
        get_catalog_mock.assert_called_once_with(1)
        get_solution_mock.assert_called_once_with(coordinates)
        search_mock.assert_called_once_with(coordinates)
        retrieve_and_load_mock.assert_called_once()

    @patch("album.core.controller.collection.collection_manager.dict_to_coordinates", return_value="myCoordinates")
    def test_resolve_download(self, dict_to_coordinates_mock):
        # prepare
        resolve_catalog = Catalog("aNiceId", "aNiceName", "aValidPath")
        retrieve_solution = MagicMock(return_value=None)
        resolve_catalog.retrieve_solution = retrieve_solution

        resolve_path = Path(self.tmp_dir.name).joinpath("myResolvedSolution")
        resolve = ResolveResult(path=resolve_path, catalog=resolve_catalog, solution_attrs={})

        _resolve = MagicMock(return_value=resolve)
        self.collection_manager._resolve = _resolve

        # call
        r = self.collection_manager.resolve_download("myInput")

        # assert
        _resolve.assert_called_once_with("myInput")
        dict_to_coordinates_mock.assert_called_once_with({})
        retrieve_solution.assert_called_once_with("myCoordinates")
        self.assertEqual(resolve, r)

    def test_resolve_download_file_exists(self):
        # prepare
        resolve_catalog = Catalog("aNiceId", "aNiceName", "aValidPath")
        retrieve_solution = MagicMock(return_value=None)
        resolve_catalog.retrieve_solution = retrieve_solution

        resolve_path = Path(self.tmp_dir.name).joinpath("myResolvedSolution")
        resolve_path.touch()
        resolve = ResolveResult(path=resolve_path, catalog=resolve_catalog, solution_attrs={})

        _resolve = MagicMock(return_value=resolve)
        self.collection_manager._resolve = _resolve

        # call
        r = self.collection_manager.resolve_download("myInput")

        # assert
        _resolve.assert_called_once_with("myInput")
        retrieve_solution.assert_not_called()
        self.assertEqual(resolve, r)

    @patch('album.core.controller.collection.collection_manager.load')
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

        # call
        r = self.collection_manager.resolve_dependency_require_installation_and_load(
            {"group": "g", "name": "n", "version": "v"})

        self.assertEqual(get_solution_file_mock.return_value, r.path)
        self.assertEqual(self.active_solution, r.active_solution)

        get_solutions_by_grp_name_version.assert_called_once_with(Coordinates("g", "n", "v"))
        get_solution_file_mock.assert_called_once_with(Coordinates("g", "n", "v"))
        load_mock.assert_called_once_with("aValidPath")
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
    def test__search_by_coordinates(self):
        # todo: implement
        pass

    def test__search_in_local_catalog(self):
        coordinates = Coordinates("g", "n", "v")
        search_mock = MagicMock(return_value={"res": "res"})
        self.collection_manager._search_in_specific_catalog = search_mock
        res = self.collection_manager._search_in_local_catalog(coordinates)
        self.assertEqual(search_mock.return_value, res)
        search_mock.assert_called_once_with(self.collection_manager.catalogs().get_local_catalog().catalog_id, coordinates)

    @unittest.skip("Needs to be implemented!")
    def test__search_in_specific_catalog(self):
        # todo: implement
        pass


if __name__ == '__main__':
    unittest.main()

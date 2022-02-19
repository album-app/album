import unittest
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from album.core.model.catalog import Catalog
from album.core.model.collection_index import CollectionIndex
from album.core.model.resolve_result import ResolveResult
from album.runner.core.model.coordinates import Coordinates
from album.runner.core.model.solution import Solution
from test.unit.test_unit_core_common import TestCatalogAndCollectionCommon


class TestCollectionManager(TestCatalogAndCollectionCommon):

    def setUp(self):
        super().setUp()
        self.setup_test_catalogs()
        self.setup_collection()
        self.fill_catalog_collection()
        self.setup_solution_no_env()

    @unittest.skip("Needs to be implemented!")
    def test_load_or_create_collection(self):
        pass

    def test_catalogs(self):
        self.assertIsNotNone(self.album_controller.collection_manager().catalogs())

    def test_solutions(self):
        self.assertIsNotNone(self.album_controller.collection_manager().solutions())

    def test_get_index_as_dict(self):
        expected_dict = {'catalogs': [
            {
                'catalog_id': 1,
                'name': 'cache_catalog',
                'src': str(Path(self.tmp_dir.name).joinpath("catalogs", "cache_catalog")),
                'path': str(Path(self.tmp_dir.name).joinpath("catalogs", "cache_catalog")),
                'deletable': 0,
                'branch_name': "main",
                'type': "direct",
                'solutions': []
            },
            {
                'catalog_id': 2,
                'name': 'test_catalog',
                'src': str(Path(self.tmp_dir.name).joinpath("my-catalogs", "test_catalog")),
                'path': str(Path(self.tmp_dir.name).joinpath("catalogs", "test_catalog")),
                'deletable': 0,
                'branch_name': "main",
                'type': "direct",
                'solutions': []
            }, {
                'catalog_id': 3,
                'name': 'default',
                'src': 'https://gitlab.com/album-app/catalogs/default',
                'path': str(Path(self.tmp_dir.name).joinpath("catalogs", "default")),
                'deletable': 1,
                'branch_name': "main",
                'type': "direct",
                'solutions': []
            },
            {
                'catalog_id': 4,
                'name': 'test_catalog2',
                'src': str(Path(self.tmp_dir.name).joinpath("my-catalogs", "test_catalog2")),
                'path': str(Path(self.tmp_dir.name).joinpath("catalogs", "test_catalog2")),
                'deletable': 1,
                'branch_name': "main",
                'type': "direct",
                'solutions': []
            }
        ]}
        self.assertEqual(expected_dict, self.album_controller.collection_manager().get_index_as_dict())

    @unittest.skip("Needs to be implemented!")
    def test_resolve_require_installation(self):
        # todo: implement
        pass

    @patch('album.core.controller.collection.collection_manager.check_file_or_url')
    @patch('album.core.controller.state_manager.StateManager.load')
    def test_resolve_require_installation_and_load(self, load_mock, check_file_or_url_mock):
        # mocks
        search_mock = MagicMock(
            return_value=CollectionIndex.CollectionSolution(
                internal={"catalog_id": 1, "installed": True},
                setup={"group": "grp", "name": "name", "version": "version"}))
        self.album_controller.collection_manager()._search = search_mock
        load_mock.return_value = Solution({"group": "grp", "name": "name", "version": "version"})
        check_file_or_url_mock.return_value = None

        # call
        self.album_controller.collection_manager().resolve_installed_and_load("grp:name:version")

        # assert
        check_file_or_url_mock.assert_called_once_with("grp:name:version",
                                                       self.album_controller.configuration().cache_path_download())

    @unittest.skip("Needs to be implemented!")
    def test_resolve_require_installation_and_load_valid_path(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_resolve_download_and_load(self):
        # todo: implement
        pass

    @patch('album.core.controller.collection.solution_handler.SolutionHandler.set_cache_paths')
    def test_resolve_download_and_load_catalog_coordinates(self, set_cache_paths_mock):
        catalog = Catalog("aNiceId", "aNiceName", "aValidPath")
        coordinates = Coordinates("g", "n", "v")
        # mocks
        search_mock = MagicMock(return_value=CollectionIndex.CollectionSolution(
            setup={"group": "g", "name": "n", "version": "v"}))
        retrieve_and_load_mock = MagicMock()
        retrieve_and_load_mock.side_effect = lambda x: setattr(x, "loaded_solution",
                                                               lambda: Solution(self.solution_default_dict))
        get_solution_file_mock = MagicMock(return_value="path/to/solution")

        self.album_controller.collection_manager()._search_in_specific_catalog = search_mock
        self.album_controller.collection_manager().retrieve_and_load_resolve_result = retrieve_and_load_mock
        self.solution_handler.get_solution_file = get_solution_file_mock

        # call
        res = self.album_controller.collection_manager().resolve_and_load_catalog_coordinates(catalog, coordinates)

        # assert
        self.assertEqual(catalog, res.catalog())
        self.assertEqual(search_mock.return_value, res.database_entry())

        get_solution_file_mock.assert_called_once_with(catalog, coordinates)
        search_mock.assert_called_once_with(catalog.catalog_id(), coordinates)
        retrieve_and_load_mock.assert_called_once()
        set_cache_paths_mock.assert_called_once()

    @patch('album.core.controller.collection.solution_handler.SolutionHandler.set_cache_paths')
    def test_resolve_download_and_load_coordinates(self, set_cache_paths_mock):
        coordinates = Coordinates("g", "n", "v")
        local_catalog = self.album_controller.collection_manager().catalogs().get_cache_catalog()

        # mocks
        get_catalog_mock = MagicMock(return_value=local_catalog)
        get_solution_mock = MagicMock(return_value="path/to/solution")
        search_mock = MagicMock(return_value=CollectionIndex.CollectionSolution(internal={"catalog_id": 1}))
        retrieve_and_load_mock = MagicMock()
        retrieve_and_load_mock.side_effect = lambda x: setattr(x, "loaded_solution",
                                                               lambda: Solution(self.solution_default_dict))

        self.album_controller.collection_manager()._search_by_coordinates = search_mock
        self.album_controller.collection_manager().catalogs().get_by_id = get_catalog_mock
        self.solution_handler.get_solution_file = get_solution_mock
        self.album_controller.collection_manager().retrieve_and_load_resolve_result = retrieve_and_load_mock

        # call
        res = self.album_controller.collection_manager().resolve_and_load_coordinates(coordinates)

        # assert
        self.assertEqual(local_catalog, res.catalog())
        self.assertEqual(get_solution_mock.return_value, res.path())
        self.assertEqual(search_mock.return_value, res.database_entry())

        get_catalog_mock.assert_called_once_with(1)
        get_solution_mock.assert_called_once_with(local_catalog, coordinates)
        search_mock.assert_called_once_with(coordinates)
        retrieve_and_load_mock.assert_called_once()
        set_cache_paths_mock.assert_called_once()

    def test_resolve_download(self):
        # prepare
        resolve_catalog = Catalog("aNiceId", "aNiceName", "aValidPath")
        retrieve_solution = MagicMock(return_value=None)
        self.solution_handler.retrieve_solution = retrieve_solution

        resolve_path = Path(self.tmp_dir.name).joinpath("myResolvedSolution")
        resolve = ResolveResult(
            path=resolve_path, catalog=resolve_catalog, collection_entry={}, coordinates=Coordinates("a", "b", "c")
        )

        _resolve = MagicMock(return_value=resolve)
        self.album_controller.collection_manager()._resolve = _resolve

        # call
        r = self.album_controller.collection_manager().resolve("myInput")

        # assert
        _resolve.assert_called_once_with("myInput")
        retrieve_solution.assert_called_once_with(resolve_catalog, Coordinates("a", "b", "c"))
        self.assertEqual(resolve, r)

    def test_resolve_download_file_exists(self):
        # prepare
        resolve_catalog = Catalog("aNiceId", "aNiceName", "aValidPath")
        retrieve_solution = MagicMock(return_value=None)
        resolve_catalog.retrieve_solution = retrieve_solution

        resolve_path = Path(self.tmp_dir.name).joinpath("myResolvedSolution")
        resolve_path.touch()
        resolve = ResolveResult(path=resolve_path, catalog=resolve_catalog, collection_entry={}, coordinates=None)

        _resolve = MagicMock(return_value=resolve)
        self.album_controller.collection_manager()._resolve = _resolve

        # call
        r = self.album_controller.collection_manager().resolve("myInput")

        # assert
        _resolve.assert_called_once_with("myInput")
        retrieve_solution.assert_not_called()
        self.assertEqual(resolve, r)

    @unittest.skip("Needs to be implemented!")
    def test_resolve_parent(self):
        # todo: implement
        pass

    @patch('album.core.controller.collection.collection_manager.check_file_or_url')
    def test__resolve_case_local_file(self, check_file_or_url_mock):
        # prepare
        f = Path(self.tmp_dir.name).joinpath("mySolution.py")
        f.touch()

        # mock
        check_file_or_url_mock.return_value = Path(f.name)

        # get_doi_from_input <- deliberately not patched

        _search_for_local_file_mock = MagicMock(return_value=None)  # no entry in DB found
        self.album_controller.collection_manager()._search_for_local_file = _search_for_local_file_mock

        _search_mock = MagicMock(return_value=None)
        self.album_controller.collection_manager()._search = _search_mock

        _search_doi_mock = MagicMock(return_value=None)
        self.album_controller.collection_manager()._search_doi = _search_doi_mock

        # call
        resolve_result = self.album_controller.collection_manager()._resolve(f.name)

        # assert
        expected_result = ResolveResult(
            path=Path(f.name),
            catalog=self.album_controller.collection_manager().catalogs().get_cache_catalog(),
            coordinates=None,
            collection_entry=None
        )

        self.assertEqual(expected_result, resolve_result)

        # assert mocks
        _search_for_local_file_mock.assert_called_once_with(Path(f.name))
        _search_mock.assert_not_called()
        _search_doi_mock.assert_not_called()

    @patch('album.core.controller.collection.collection_manager.check_doi')
    @patch('album.core.controller.collection.collection_manager.check_file_or_url', return_value=None)
    def test__resolve_case_doi(self, _, check_doi_mock):
        # prepare
        input = "doi:10.5072/zenodo.931388"  # a zenodo doi
        f = Path(self.tmp_dir.name).joinpath("myDOISolution.py")
        f.touch()

        # mocks
        _search_for_local_file_mock = MagicMock(return_value=None)
        self.album_controller.collection_manager()._search_for_local_file = _search_for_local_file_mock

        _search_mock = MagicMock(return_value=None)
        self.album_controller.collection_manager()._search = _search_mock

        _search_doi_mock = MagicMock(return_value=None)  # DOI not in any catalog
        self.album_controller.collection_manager()._search_doi = _search_doi_mock

        check_doi_mock.return_value = Path(f.name)  # downloaded solution behind the doi

        # call
        resolve_result = self.album_controller.collection_manager()._resolve(input)

        # assert
        expected_result = ResolveResult(
            path=Path(f.name),
            catalog=self.album_controller.collection_manager().catalogs().get_cache_catalog(),
            coordinates=None,
            collection_entry=None
        )

        self.assertEqual(expected_result, resolve_result)

        # assert mocks
        _search_for_local_file_mock.assert_not_called()
        _search_mock.assert_not_called()
        _search_doi_mock.assert_called_once_with("10.5072/zenodo.931388")
        check_doi_mock.assert_called_once_with(
            "10.5072/zenodo.931388", Path(self.tmp_dir.name).joinpath("tmp")
        )

    @patch('album.core.controller.collection.collection_manager.check_file_or_url', return_value=None)
    def test__resolve_case_grp_name_version_not_found(self, _):
        # prepare
        this_input = "grp:name:version"

        # mocks
        _search_for_local_file_mock = MagicMock(return_value=None)
        self.album_controller.collection_manager()._search_for_local_file = _search_for_local_file_mock

        _search_mock = MagicMock(return_value=None)
        self.album_controller.collection_manager()._search = _search_mock

        _search_doi_mock = MagicMock(return_value=None)  # DOI not in any catalog
        self.album_controller.collection_manager()._search_doi = _search_doi_mock

        # call
        with self.assertRaises(LookupError):
            self.album_controller.collection_manager()._resolve(this_input)

        # assert mocks
        _search_for_local_file_mock.assert_not_called()
        _search_mock.assert_called_once_with(this_input)
        _search_doi_mock.assert_not_called()

    @unittest.skip("Needs to be implemented!")
    def test__search_local_file(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__search(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__search_doi(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__search_by_coordinates(self):
        # todo: implement
        pass

    def test__search_in_local_catalog(self):
        coordinates = Coordinates("g", "n", "v")
        search_mock = MagicMock(return_value={"res": "res"})
        self.album_controller.collection_manager()._search_in_specific_catalog = search_mock
        res = self.album_controller.collection_manager()._search_in_local_catalog(coordinates)
        self.assertEqual(search_mock.return_value, res)
        search_mock.assert_called_once_with(self.album_controller.collection_manager().catalogs().get_cache_catalog().catalog_id(),
                                            coordinates)

    @unittest.skip("Needs to be implemented!")
    def test__search_in_specific_catalog(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__search_in_catalogs(self):
        # todo: implement
        pass

    def test_retrieve_and_load_resolve_result(self):
        # todo: implement
        pass

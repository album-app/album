import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from album.core.api.model.catalog_updates import ChangeType
from album.core.model.catalog import Catalog
from album.core.model.catalog_updates import SolutionChange
from album.core.model.collection_index import CollectionIndex
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import get_link_target
from album.runner.core.model.coordinates import Coordinates
from album.runner.core.model.solution import Solution
from test.unit.core.controller.collection.test_collection_manager import TestCatalogAndCollectionCommon
from test.unit.test_unit_core_common import EmptyTestClass


class TestSolutionHandler(TestCatalogAndCollectionCommon):

    def setUp(self):
        super().setUp()
        self.setup_test_catalogs()
        self.setup_collection()
        self.fill_catalog_collection()
        catalog_src = Path(self.tmp_dir.name).joinpath("testRepo")
        self.album_controller.catalogs().create_new_metadata(catalog_src, "test", "direct")
        catalog_path = Path(self.tmp_dir.name).joinpath("testPath")
        catalog_path.mkdir(parents=True)

        self.catalog = Catalog(0, "test", src=catalog_src, path=catalog_path)
        self.solution_handler = self.album_controller.collection_manager().solution_handler

    def tearDown(self) -> None:
        super().tearDown()

    @patch('album.core.controller.collection.solution_handler.copy')
    @patch('album.core.controller.collection.solution_handler.copy_folder')
    def test_add_or_replace_folder_call(self, copy_folder_mock, copy_mock):
        self.setup_solution_no_env()

        catalog = EmptyTestClass()
        catalog.catalog_id = lambda: 5

        # mock
        add_or_replace_solution = MagicMock()
        self.album_controller.collection_manager().get_collection_index().add_or_replace_solution = add_or_replace_solution

        get_solution_path = MagicMock(return_value="myCopyPath")
        self.solution_handler.get_solution_path = get_solution_path

        # call
        self.solution_handler.add_or_replace(catalog, self.active_solution, self.tmp_dir.name)

        # assert
        add_or_replace_solution.assert_called_once_with(
            5, self.active_solution.coordinates(), self.solution_default_dict
        )
        get_solution_path.assert_called_once_with(catalog, Coordinates("tsg", "tsn", "tsv"))
        copy_folder_mock.assert_called_once_with(self.tmp_dir.name, "myCopyPath", copy_root_folder=False)
        copy_mock.assert_not_called()

    @patch('album.core.controller.collection.solution_handler.copy')
    @patch('album.core.controller.collection.solution_handler.copy_folder')
    def test_add_or_replace_file_call(self, copy_folder_mock, copy_mock):
        self.setup_solution_no_env()

        catalog = EmptyTestClass()
        catalog.catalog_id = lambda: 5

        # mock
        add_or_replace_solution = MagicMock()
        self.album_controller.collection_manager().get_collection_index().add_or_replace_solution = add_or_replace_solution

        get_solution_path = MagicMock(return_value=Path("myCopyPath"))
        self.solution_handler.get_solution_path = get_solution_path

        # call
        self.solution_handler.add_or_replace(catalog, self.active_solution, self.closed_tmp_file.name)

        # assert
        add_or_replace_solution.assert_called_once_with(
            5, self.active_solution.coordinates(), self.solution_default_dict
        )
        get_solution_path.assert_called_once_with(catalog, Coordinates("tsg", "tsn", "tsv"))
        copy_folder_mock.assert_not_called()
        copy_mock.assert_called_once_with(self.closed_tmp_file.name, Path("myCopyPath").joinpath("solution.py"))

    def test_add_to_cache_catalog(self):
        self.setup_solution_no_env()
        cache_catalog = EmptyTestClass()
        cache_catalog.catalog_id = lambda: 5

        # mock
        add_or_replace = MagicMock()
        self.solution_handler.add_or_replace = add_or_replace

        self.album_controller.catalogs().get_cache_catalog = MagicMock(return_value=cache_catalog)

        # call
        self.solution_handler.add_to_cache_catalog(self.active_solution, "mypath")

        # assert
        add_or_replace.assert_called_once_with(cache_catalog, self.active_solution, "mypath")

    def test_set_parent(self):
        # prepare
        catalog_parent = EmptyTestClass()
        catalog_parent.catalog_id = lambda: 0

        catalog_child = EmptyTestClass()
        catalog_child.catalog_id = lambda: 1

        parent_entry = EmptyTestClass()
        parent_entry.internal = lambda: {"collection_id": 5}
        child_entry = EmptyTestClass()
        child_entry.internal = lambda: {"collection_id": 10}

        # mock
        get_solution_by_catalog_grp_name_version = MagicMock()
        get_solution_by_catalog_grp_name_version.side_effect = [parent_entry, child_entry]
        self.solution_handler._get_collection_index().get_solution_by_catalog_grp_name_version = get_solution_by_catalog_grp_name_version

        insert_collection_collection = MagicMock()
        self.solution_handler._get_collection_index().insert_collection_collection = insert_collection_collection

        # call
        self.solution_handler.set_parent(
            catalog_parent, catalog_child, Coordinates("a", "p", "0"), Coordinates("a", "c", "0")
        )

        # assert
        insert_collection_collection.assert_called_once_with(5, 10, 0, 1)

    def test_remove_parent(self):
        catalog = EmptyTestClass()
        catalog.catalog_id = lambda: 0

        parent_entry = EmptyTestClass()
        parent_entry.internal = lambda: {"collection_id": 5}

        # mock
        get_solution_by_catalog_grp_name_version = MagicMock(return_value=parent_entry)
        self.solution_handler._get_collection_index().get_solution_by_catalog_grp_name_version = get_solution_by_catalog_grp_name_version

        remove_parent = MagicMock()
        self.solution_handler._get_collection_index().remove_parent = remove_parent

        # call
        self.solution_handler.remove_parent(catalog, Coordinates("a", "b", "c"))

        # assert
        remove_parent.assert_called_once_with(5)

    def test_remove_solution(self):
        # prepare
        catalog = EmptyTestClass()
        catalog.catalog_id = lambda: 0

        c = Coordinates("a", "b", "c")

        # mock
        remove_solution = MagicMock()
        self.solution_handler._get_collection_index().remove_solution = remove_solution

        # call
        self.solution_handler.remove_solution(catalog, c)

        # assert
        remove_solution.assert_called_once_with(0, c)

    def test_update_solution(self):
        # prepare
        catalog = EmptyTestClass()
        catalog.catalog_id = lambda: 0

        c = Coordinates("a", "b", "c")

        # mock
        update_solution = MagicMock()
        self.solution_handler._get_collection_index().update_solution = update_solution

        # call
        self.solution_handler.update_solution(catalog, c, {})

        # assert
        update_solution.assert_called_once_with(0, c, {}, CollectionIndex.get_collection_column_keys())

    def test_apply_change_ADDED(self):
        # prepare
        coordinates = Coordinates("g", "n", "v")
        change = SolutionChange(coordinates, ChangeType.ADDED)

        # mocks
        empty_catalog = EmptyTestClass()
        empty_catalog.get_solution_by_coordinates = MagicMock()
        empty_catalog.close = MagicMock()
        self.catalog._catalog_index = empty_catalog

        add_or_replace_solution = MagicMock()
        self.album_controller.collection_manager().get_collection_index().add_or_replace_solution = add_or_replace_solution

        remove_solution = MagicMock()
        self.solution_handler.remove_solution = remove_solution

        retrieve_solution = MagicMock()
        self.solution_handler.retrieve_solution = retrieve_solution

        # call
        self.solution_handler.apply_change(self.catalog, change, override=False)

        # assert
        add_or_replace_solution.assert_called_once()
        remove_solution.assert_not_called()
        retrieve_solution.assert_not_called()

    def test_apply_change_REMOVED(self):
        # prepare
        coordinates = Coordinates("g", "n", "v")
        change = SolutionChange(coordinates, ChangeType.REMOVED)

        # mocks
        remove_solution = MagicMock()
        self.solution_handler.remove_solution = remove_solution

        retrieve_solution = MagicMock()
        self.solution_handler.retrieve_solution = retrieve_solution

        # call
        self.solution_handler.apply_change(self.catalog, change, override=False)

        # assert
        remove_solution.assert_called_once()
        retrieve_solution.assert_not_called()

    def test_apply_change_CHANGED_no_override(self):
        # prepare
        coordinates = Coordinates("g", "n", "v")
        change = SolutionChange(coordinates, ChangeType.CHANGED)

        # mocks
        empty_catalog = EmptyTestClass()
        empty_catalog.get_solution_by_coordinates = MagicMock()
        empty_catalog.close = MagicMock()
        self.catalog._catalog_index = empty_catalog

        add_or_replace_solution = MagicMock()
        self.album_controller.collection_manager().get_collection_index().add_or_replace_solution = add_or_replace_solution

        _set_old_db_stat = MagicMock()
        self.solution_handler._set_old_db_stat = _set_old_db_stat

        remove_solution = MagicMock()
        self.solution_handler.remove_solution = remove_solution

        retrieve_solution = MagicMock()
        self.solution_handler.retrieve_solution = retrieve_solution

        # call
        self.solution_handler.apply_change(self.catalog, change, override=False)

        # assert
        add_or_replace_solution.assert_called_once()
        remove_solution.assert_not_called()  # at least not directly
        _set_old_db_stat.assert_called_once_with(self.catalog, change)
        retrieve_solution.assert_not_called()

    def test_apply_change_CHANGED_override_uninstalled(self):
        # prepare
        coordinates = Coordinates("g", "n", "v")
        change = SolutionChange(coordinates, ChangeType.CHANGED)

        # mocks
        empty_catalog = EmptyTestClass()
        empty_catalog.get_solution_by_coordinates = MagicMock()
        empty_catalog.close = MagicMock()
        self.catalog._catalog_index = empty_catalog

        add_or_replace_solution = MagicMock()
        self.album_controller.collection_manager().get_collection_index().add_or_replace_solution = add_or_replace_solution

        remove_solution = MagicMock()
        self.solution_handler.remove_solution = remove_solution

        _set_old_db_stat = MagicMock()
        self.solution_handler._set_old_db_stat = _set_old_db_stat

        retrieve_solution = MagicMock()
        self.solution_handler.retrieve_solution = retrieve_solution

        is_installed = MagicMock(return_value=False)
        self.solution_handler.is_installed = is_installed

        # call
        self.solution_handler.apply_change(self.catalog, change, override=True)

        # assert
        add_or_replace_solution.assert_called_once()
        remove_solution.assert_not_called()
        _set_old_db_stat.assert_called_once_with(self.catalog, change)
        retrieve_solution.assert_not_called()

    def test_apply_change_CHANGED_override_installed_but_cache(self):
        # prepare
        coordinates = Coordinates("g", "n", "v")
        change = SolutionChange(coordinates, ChangeType.CHANGED)

        # mocks
        empty_catalog = EmptyTestClass()
        empty_catalog.get_solution_by_coordinates = MagicMock()
        empty_catalog.close = MagicMock()
        self.catalog._catalog_index = empty_catalog
        self.catalog.is_cache = MagicMock(return_value=True)

        add_or_replace_solution = MagicMock()
        self.album_controller.collection_manager().get_collection_index().add_or_replace_solution = add_or_replace_solution

        remove_solution = MagicMock()
        self.solution_handler.remove_solution = remove_solution

        _set_old_db_stat = MagicMock()
        self.solution_handler._set_old_db_stat = _set_old_db_stat

        retrieve_solution = MagicMock()
        self.solution_handler.retrieve_solution = retrieve_solution

        is_installed = MagicMock(return_value=True)
        self.solution_handler.is_installed = is_installed

        # call
        self.solution_handler.apply_change(self.catalog, change, override=True)

        # assert
        add_or_replace_solution.assert_called_once()
        remove_solution.assert_not_called()
        _set_old_db_stat.assert_called_once_with(self.catalog, change)
        retrieve_solution.assert_not_called()

    def test_apply_change_CHANGED_override_installed_no_cache(self):
        # prepare
        coordinates = Coordinates("g", "n", "v")
        change = SolutionChange(coordinates, ChangeType.CHANGED, solution_status={"old_status": 1, "parent": "yes"})

        # mocks
        empty_catalog = EmptyTestClass()
        empty_catalog.get_solution_by_coordinates = MagicMock()
        empty_catalog.close = MagicMock()
        self.catalog._catalog_index = empty_catalog
        self.catalog.is_cache = MagicMock(return_value=False)

        add_or_replace_solution = MagicMock()
        self.album_controller.collection_manager().get_collection_index().add_or_replace_solution = add_or_replace_solution

        _set_old_db_stat = MagicMock()
        self.solution_handler._set_old_db_stat = _set_old_db_stat

        remove_solution = MagicMock()
        self.solution_handler.remove_solution = remove_solution

        retrieve_solution = MagicMock()
        self.solution_handler.retrieve_solution = retrieve_solution

        is_installed = MagicMock(return_value=True)
        self.solution_handler.is_installed = is_installed

        # call
        self.solution_handler.apply_change(self.catalog, change, override=True)

        # assert
        add_or_replace_solution.assert_called_once()
        remove_solution.assert_not_called()
        _set_old_db_stat.assert_called_once_with(self.catalog, change)
        retrieve_solution.assert_called_once()

    def test__set_old_db_stat(self):
        coordinates = Coordinates("g", "n", "v")
        change = SolutionChange(coordinates, ChangeType.CHANGED, solution_status={"old_status": 1, "parent": "yes"})

        empty_catalog = EmptyTestClass()
        empty_catalog.catalog_id = lambda: 5

        # mock
        _get_db_status_dict = MagicMock(return_value={"parent": "yes"})
        self.solution_handler._get_db_status_dict = _get_db_status_dict

        update_solution = MagicMock()
        self.solution_handler.update_solution = update_solution

        _set_parent_from_entry = MagicMock()
        self.solution_handler._set_parent_from_entry = _set_parent_from_entry

        get_solution_by_catalog_grp_name_version = MagicMock(return_value="internal_solution")
        self.album_controller.collection_manager().get_collection_index().get_solution_by_catalog_grp_name_version = get_solution_by_catalog_grp_name_version

        # call
        self.solution_handler._set_old_db_stat(empty_catalog, change)

        # assert
        _get_db_status_dict.assert_called_once_with({"old_status": 1, "parent": "yes"})
        update_solution.assert_called_once_with(empty_catalog, coordinates, {"parent": "yes"})
        _set_parent_from_entry.assert_called_once_with("yes", "internal_solution")
        get_solution_by_catalog_grp_name_version.assert_called_once_with(5, coordinates)

    @unittest.skip("Needs to be implemented!")
    def test_set_installed(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_set_uninstalled(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_set_installation_unfinished(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_is_installed(self):
        # todo: implement
        pass

    def test_get_solution_path(self):
        # call
        file = Path(self.solution_handler.get_solution_path(self.catalog, Coordinates("g", "n", "v"))).resolve()
        self.assertEqual(
            get_link_target(
                self.catalog.path().joinpath(DefaultValues.cache_path_solution_prefix.value, "g", "n", "v")).resolve(),
            file
        )

    def test_get_solution_file(self):
        # call
        file = Path(self.solution_handler.get_solution_file(self.catalog, Coordinates("g", "n", "v"))).resolve()
        res = get_link_target(
            self.catalog.path().joinpath(DefaultValues.cache_path_solution_prefix.value, "g", "n", "v")).joinpath(
            "solution.py")
        self.assertEqual(res.resolve(), file)

    def test_get_solution_zip(self):
        # call
        solution_zip = Path(self.solution_handler.get_solution_zip(self.catalog, Coordinates("g", "n", "v"))).resolve()
        res = get_link_target(
            self.catalog.path().joinpath(DefaultValues.cache_path_solution_prefix.value, "g", "n", "v")).joinpath(
            "g_n_v.zip")
        self.assertEqual(res.resolve(), solution_zip)

    def test_get_solution_zip_suffix(self):
        res = Path("").joinpath(DefaultValues.cache_path_solution_prefix.value, "g", "n", "v", "g_n_v.zip")

        # call
        self.assertEqual(res, self.solution_handler.get_solution_zip_suffix(Coordinates("g", "n", "v")))

    @patch("album.core.controller.collection.solution_handler.SolutionHandler._download_solution_zip")
    @patch("album.core.controller.collection.solution_handler.unzip_archive", return_value=Path("a/Path"))
    def test_retrieve_solution(self, unzip_mock, dl_mock):
        # prepare
        self.catalog = Catalog(self.catalog.catalog_id(), self.catalog.name(), self.catalog.path(),
                               "http://NonsenseUrl.git")
        self.catalog.is_cache = MagicMock(return_value=False)

        # call & assert
        coordinates = Coordinates("g", "n", "v")
        solution_path = self.solution_handler.retrieve_solution(self.catalog, coordinates)

        # assert
        dl_path = get_link_target(self.catalog.path().joinpath(
            DefaultValues.cache_path_solution_prefix.value, "g", "n", "v"
        )).joinpath("g_n_v.zip")
        res = Path("a/Path").joinpath(DefaultValues.solution_default_name.value)
        self.assertEqual(res, solution_path)

        dl_mock.assert_called_once_with("http://NonsenseUrl.git", coordinates, dl_path, "main")
        unzip_mock.assert_called_once_with(dl_path)

    def test_set_cache_paths(self):
        config = self.album_controller.configuration()

        active_solution = Solution(self.solution_default_dict)
        path = self.album_controller.configuration().get_cache_path_catalog("catalog_name_solution_lives_in")
        catalog = Catalog(0, "catalog_name_solution_lives_in", path)
        self.solution_handler.set_cache_paths(active_solution, catalog)

        self.assertEqual(
            Path(config.lnk_path()).joinpath('data', '0').resolve(),
            active_solution.installation().data_path().resolve()
        )
        self.assertEqual(
            Path(config.lnk_path()).joinpath('app', '0').resolve(),
            active_solution.installation().app_path().resolve()
        )
        self.assertEqual(
            Path(config.lnk_path()).joinpath('pck', '0').resolve(),
            active_solution.installation().package_path().resolve()
        )
        self.assertEqual(
            Path(config.lnk_path()).joinpath('icache', '0').resolve(),
            active_solution.installation().internal_cache_path().resolve()
        )
        self.assertEqual(
            Path(config.lnk_path()).joinpath('ucache', '0').resolve(),
            active_solution.installation().user_cache_path().resolve()
        )

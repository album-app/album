import unittest
from pathlib import Path
from test.unit.core.controller.collection.test_collection_manager import (
    TestCatalogAndCollectionCommon,
)
from test.unit.test_unit_core_common import EmptyTestClass
from unittest.mock import MagicMock, create_autospec, patch

from album.core.api.model.catalog_updates import ChangeType
from album.core.model.catalog import Catalog
from album.core.model.catalog_index import CatalogIndex
from album.core.model.catalog_updates import SolutionChange
from album.core.model.collection_index import CollectionIndex
from album.core.model.default_values import DefaultValues
from album.core.model.resolve_result import ResolveResult
from album.core.utils.operations.file_operations import get_link_target
from album.runner.core.model.coordinates import Coordinates
from album.runner.core.model.solution import Solution


class TestSolutionHandler(TestCatalogAndCollectionCommon):
    def setUp(self):
        super().setUp()
        self.setup_test_catalogs()
        self.setup_collection()
        self.fill_catalog_collection()
        catalog_src = Path(self.tmp_dir.name).joinpath("testRepo")
        self.album_controller.catalogs().create_new_metadata(
            catalog_src, "test", "direct"
        )
        catalog_path = Path(self.tmp_dir.name).joinpath("testPath")
        catalog_path.mkdir(parents=True)

        self.catalog = Catalog(0, "test", src=str(catalog_src), path=str(catalog_path))
        self.catalog_index = CatalogIndex(
            "n", Path(self.tmp_dir.name).joinpath("album_catalog_index.db")
        )
        self.catalog._catalog_index = self.catalog_index
        self.solution_handler = (
            self.album_controller.collection_manager().solution_handler
        )

    def tearDown(self) -> None:
        super().tearDown()

    @patch("album.core.controller.collection.solution_handler.copy")
    @patch("album.core.controller.collection.solution_handler.copy_folder")
    @patch("album.core.controller.collection.solution_handler.get_deploy_dict")
    def test_add_or_replace_folder_call(
        self, get_deploy_dict_mock, copy_folder_mock, copy_mock
    ):
        get_deploy_dict_mock.return_value = self.solution_default_dict

        catalog = EmptyTestClass()
        catalog.catalog_id = lambda: 5
        loaded_solution = Solution(self.solution_default_dict)
        solution = ResolveResult(
            Path("path").joinpath("solution.py"),
            catalog,
            None,
            Coordinates("tsg", "tsn", "tsv"),
            loaded_solution=loaded_solution,
        )

        # mock
        add_or_replace_solution = MagicMock()
        self.album_controller.collection_manager().get_collection_index().add_or_replace_solution = (
            add_or_replace_solution
        )

        get_solution_path = MagicMock(return_value=Path("myCopyPath"))
        self.solution_handler.get_solution_package_path = get_solution_path

        # call
        self.solution_handler.add_or_replace(catalog, solution)

        # assert
        add_or_replace_solution.assert_called_once_with(
            5, Coordinates("tsg", "tsn", "tsv"), self.solution_default_dict
        )
        get_solution_path.assert_called_once_with(
            catalog, Coordinates("tsg", "tsn", "tsv")
        )
        copy_folder_mock.assert_called_once_with(
            Path("path"), Path("myCopyPath"), copy_root_folder=False
        )
        copy_mock.assert_not_called()

    @patch("album.core.controller.collection.solution_handler.copy")
    @patch("album.core.controller.collection.solution_handler.copy_folder")
    def test_add_or_replace_file_call(self, copy_folder_mock, copy_mock):
        self.setup_solution_no_env()
        solution = create_autospec(ResolveResult)
        solution.loaded_solution = lambda: self.active_solution
        solution.is_single_file = lambda: True

        catalog = EmptyTestClass()
        catalog.catalog_id = lambda: 5

        # mock
        add_or_replace_solution = MagicMock()
        self.album_controller.collection_manager().get_collection_index().add_or_replace_solution = (
            add_or_replace_solution
        )

        get_solution_path = MagicMock(return_value=Path("myCopyPath"))
        self.solution_handler.get_solution_package_path = get_solution_path

        # call
        self.solution_handler.add_or_replace(catalog, solution)

        # assert
        add_or_replace_solution.assert_called_once_with(
            5, solution.coordinates(), self.solution_default_dict
        )
        get_solution_path.assert_called_once_with(
            catalog, Coordinates("tsg", "tsn", "tsv")
        )
        copy_folder_mock.assert_not_called()
        copy_mock.assert_called_once_with(
            solution.path(), Path("myCopyPath").joinpath("solution.py")
        )

    def test_add_to_cache_catalog(self):
        self.setup_solution_no_env()
        cache_catalog = EmptyTestClass()
        cache_catalog.catalog_id = lambda: 5

        # mock
        add_or_replace = MagicMock()
        self.solution_handler.add_or_replace = add_or_replace

        self.album_controller.catalogs().get_cache_catalog = MagicMock(
            return_value=cache_catalog
        )

        # call
        self.solution_handler.add_to_cache_catalog(self.active_solution)

        # assert
        add_or_replace.assert_called_once_with(cache_catalog, self.active_solution)

    def test_set_parent(self):
        # prepare
        parent_entry = EmptyTestClass()
        parent_entry.internal = lambda: {"collection_id": 5, "catalog_id": 0}
        child_entry = EmptyTestClass()
        child_entry.internal = lambda: {"collection_id": 10, "catalog_id": 1}

        # mock
        remove_parent = MagicMock()
        self.solution_handler._get_collection_index().remove_parent = remove_parent
        insert_collection_collection = MagicMock()
        self.solution_handler._get_collection_index().insert_collection_collection = (
            insert_collection_collection
        )

        # call
        self.solution_handler.set_parent(parent_entry, child_entry)

        # assert: a link to an earlier parent is replaced
        remove_parent.assert_called_once_with(10, close=False)
        insert_collection_collection.assert_called_once_with(5, 10, 0, 1)

    def test_remove_parent(self):
        catalog = EmptyTestClass()
        catalog.catalog_id = lambda: 0

        parent_entry = EmptyTestClass()
        parent_entry.internal = lambda: {"collection_id": 5}

        # mock
        get_solution_by_catalog_grp_name_version = MagicMock(return_value=parent_entry)
        self.solution_handler._get_collection_index().get_solution_by_catalog_grp_name_version = (
            get_solution_by_catalog_grp_name_version
        )

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
        update_solution.assert_called_once_with(
            0, c, {}, CollectionIndex.get_collection_column_keys()
        )

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
        self.album_controller.collection_manager().get_collection_index().add_or_replace_solution = (
            add_or_replace_solution
        )

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

    def _apply_change_REMOVED_to(self, installed, installation_unfinished):
        coordinates = Coordinates("g", "n", "v")
        change = SolutionChange(coordinates, ChangeType.REMOVED)

        # mocks
        entry = EmptyTestClass()
        entry.internal = lambda: {
            "installed": installed,
            "installation_unfinished": installation_unfinished,
        }
        get_solution_by_catalog_grp_name_version = MagicMock(return_value=entry)
        self.album_controller.collection_manager().get_collection_index().get_solution_by_catalog_grp_name_version = (
            get_solution_by_catalog_grp_name_version
        )

        remove_solution = MagicMock()
        self.solution_handler.remove_solution = remove_solution

        # call
        self.solution_handler.apply_change(self.catalog, change, override=False)

        get_solution_by_catalog_grp_name_version.assert_called_once_with(
            self.catalog.catalog_id(), coordinates
        )
        return remove_solution

    def test_apply_change_REMOVED_not_installed(self):
        remove_solution = self._apply_change_REMOVED_to(
            installed=0, installation_unfinished=0
        )

        remove_solution.assert_called_once_with(
            self.catalog, Coordinates("g", "n", "v")
        )

    def test_apply_change_REMOVED_installed(self):
        remove_solution = self._apply_change_REMOVED_to(
            installed=1, installation_unfinished=0
        )

        # it stays until it is uninstalled
        remove_solution.assert_not_called()
        self.assertIn(
            'Solution "g:n:v" was removed from catalog "test", but it is installed.',
            self.get_logs_as_string(),
        )

    def test_apply_change_REMOVED_installation_unfinished(self):
        remove_solution = self._apply_change_REMOVED_to(
            installed=0, installation_unfinished=1
        )

        # it stays until the next installation removes its files
        remove_solution.assert_not_called()
        self.assertNotIn("was removed from catalog", self.get_logs_as_string())

    def test_apply_change_CHANGED_no_override(self):
        # prepare
        coordinates = Coordinates("g", "n", "v")
        change = SolutionChange(
            coordinates,
            ChangeType.CHANGED,
            solution_status={"installed": False, "installation_unfinished": False},
        )

        # mocks
        empty_catalog = EmptyTestClass()
        empty_catalog.get_solution_by_coordinates = MagicMock()
        empty_catalog.close = MagicMock()
        self.catalog._catalog_index = empty_catalog

        add_or_replace_solution = MagicMock()
        self.album_controller.collection_manager().get_collection_index().add_or_replace_solution = (
            add_or_replace_solution
        )

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
        _set_old_db_stat.assert_not_called()
        retrieve_solution.assert_not_called()

    def test_apply_change_CHANGED_installation_unfinished(self):
        # prepare
        coordinates = Coordinates("g", "n", "v")
        change = SolutionChange(
            coordinates,
            ChangeType.CHANGED,
            solution_status={"installed": False, "installation_unfinished": True},
        )

        # mocks
        empty_catalog = EmptyTestClass()
        empty_catalog.get_solution_by_coordinates = MagicMock()
        empty_catalog.close = MagicMock()
        self.catalog._catalog_index = empty_catalog

        add_or_replace_solution = MagicMock()
        self.album_controller.collection_manager().get_collection_index().add_or_replace_solution = (
            add_or_replace_solution
        )

        _set_old_db_stat = MagicMock()
        self.solution_handler._set_old_db_stat = _set_old_db_stat

        retrieve_solution = MagicMock()
        self.solution_handler.retrieve_solution = retrieve_solution

        # call
        self.solution_handler.apply_change(self.catalog, change, override=True)

        # assert: still marked unfinished, so the next installation removes its files
        add_or_replace_solution.assert_called_once()
        _set_old_db_stat.assert_called_once_with(self.catalog, change)
        retrieve_solution.assert_not_called()

    def test_apply_change_CHANGED_override_uninstalled(self):
        # prepare
        coordinates = Coordinates("g", "n", "v")
        change = SolutionChange(
            coordinates,
            ChangeType.CHANGED,
            solution_status={"installed": False, "installation_unfinished": False},
        )

        # mocks
        empty_catalog = EmptyTestClass()
        empty_catalog.get_solution_by_coordinates = MagicMock()
        empty_catalog.close = MagicMock()
        self.catalog._catalog_index = empty_catalog

        add_or_replace_solution = MagicMock()
        self.album_controller.collection_manager().get_collection_index().add_or_replace_solution = (
            add_or_replace_solution
        )

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
        _set_old_db_stat.assert_not_called()
        retrieve_solution.assert_not_called()

    def test_apply_change_CHANGED_override_installed_but_cache(self):
        # prepare
        coordinates = Coordinates("g", "n", "v")
        change = SolutionChange(
            coordinates, ChangeType.CHANGED, solution_status={"installed": True}
        )

        # mocks
        empty_catalog = EmptyTestClass()
        empty_catalog.get_solution_by_coordinates = MagicMock()
        empty_catalog.close = MagicMock()
        self.catalog._catalog_index = empty_catalog
        self.catalog.is_cache = MagicMock(return_value=True)

        add_or_replace_solution = MagicMock()
        self.album_controller.collection_manager().get_collection_index().add_or_replace_solution = (
            add_or_replace_solution
        )

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
        change = SolutionChange(
            coordinates,
            ChangeType.CHANGED,
            solution_status={"old_status": 1, "parent": "yes", "installed": True},
        )

        # mocks
        empty_catalog = EmptyTestClass()
        empty_catalog.get_solution_by_coordinates = MagicMock()
        empty_catalog.close = MagicMock()
        self.catalog._catalog_index = empty_catalog
        self.catalog.is_cache = MagicMock(return_value=False)

        add_or_replace_solution = MagicMock()
        self.album_controller.collection_manager().get_collection_index().add_or_replace_solution = (
            add_or_replace_solution
        )

        _set_old_db_stat = MagicMock()
        self.solution_handler._set_old_db_stat = _set_old_db_stat

        remove_solution = MagicMock()
        self.solution_handler.remove_solution = remove_solution

        retrieve_solution = MagicMock()
        self.solution_handler.retrieve_solution = retrieve_solution

        # call
        self.solution_handler.apply_change(self.catalog, change, override=True)

        # assert
        add_or_replace_solution.assert_called_once()
        remove_solution.assert_not_called()
        _set_old_db_stat.assert_called_once_with(self.catalog, change)
        retrieve_solution.assert_called_once()

    def test_apply_change_holds_the_lock_of_the_solution(self):
        coordinates = Coordinates("g", "n", "v")
        lock = self.solution_handler.get_solution_lock(self.catalog, coordinates)
        held = {}

        def _apply_change(catalog, change, override):
            held[change.change_type()] = lock.is_held_by_current_thread()

        self.solution_handler._apply_change = _apply_change

        # call
        for change_type in [ChangeType.ADDED, ChangeType.REMOVED, ChangeType.CHANGED]:
            self.solution_handler.apply_change(
                self.catalog, SolutionChange(coordinates, change_type), override=False
            )

        # assert: an installation of it in another album process is waited for
        self.assertEqual(
            {
                ChangeType.ADDED: False,
                ChangeType.REMOVED: True,
                ChangeType.CHANGED: True,
            },
            held,
        )

    def test_apply_change_CHANGED_status_when_applied(self):
        # prepare: found unfinished, finished by another album process since
        coordinates = Coordinates("g", "n", "v")
        change = SolutionChange(
            coordinates,
            ChangeType.CHANGED,
            solution_status={"installed": 0, "installation_unfinished": 1},
        )
        entry = EmptyTestClass()
        entry.internal = lambda: {"installed": 1, "installation_unfinished": 0}

        # mocks
        empty_catalog = EmptyTestClass()
        empty_catalog.get_solution_by_coordinates = MagicMock()
        empty_catalog.close = MagicMock()
        self.catalog._catalog_index = empty_catalog

        collection_index = (
            self.album_controller.collection_manager().get_collection_index()
        )
        collection_index.get_solution_by_catalog_grp_name_version = MagicMock(
            return_value=entry
        )
        collection_index.add_or_replace_solution = MagicMock()

        _set_old_db_stat = MagicMock()
        self.solution_handler._set_old_db_stat = _set_old_db_stat

        # call
        self.solution_handler.apply_change(self.catalog, change, override=False)

        # assert
        _set_old_db_stat.assert_called_once()
        self.assertEqual(
            {"installed": 1, "installation_unfinished": 0},
            _set_old_db_stat.call_args[0][1].solution_status(),
        )

    def test__set_old_db_stat(self):
        coordinates = Coordinates("g", "n", "v")
        change = SolutionChange(
            coordinates,
            ChangeType.CHANGED,
            solution_status={"old_status": 1, "parent": "yes"},
        )

        empty_catalog = EmptyTestClass()
        empty_catalog.catalog_id = lambda: 5

        # mock
        _get_db_status_dict = MagicMock(return_value={"parent": "yes"})
        self.solution_handler._get_db_status_dict = _get_db_status_dict

        update_solution = MagicMock()
        self.solution_handler.update_solution = update_solution

        set_parent = MagicMock()
        self.solution_handler.set_parent = set_parent

        get_solution_by_catalog_grp_name_version = MagicMock(
            return_value="internal_solution"
        )
        self.album_controller.collection_manager().get_collection_index().get_solution_by_catalog_grp_name_version = (
            get_solution_by_catalog_grp_name_version
        )

        # call
        self.solution_handler._set_old_db_stat(empty_catalog, change)

        # assert
        _get_db_status_dict.assert_called_once_with({"old_status": 1, "parent": "yes"})
        update_solution.assert_called_once_with(
            empty_catalog, coordinates, {"parent": "yes"}
        )
        set_parent.assert_called_once_with("yes", "internal_solution")
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

    @patch("album.core.controller.collection.solution_handler.datetime")
    def test_set_last_execution(self, datetime_mock):
        # prepare
        datetime_mock.now.return_value.isoformat.return_value = "2021-06-14T04:42:59"
        c = Coordinates("a", "b", "c")

        # mock
        update_solution = MagicMock()
        self.solution_handler.update_solution = update_solution

        # call
        self.solution_handler.set_last_execution(self.catalog, c)

        # assert
        update_solution.assert_called_once_with(
            self.catalog, c, {"last_execution": "2021-06-14T04:42:59"}
        )

    @unittest.skip("Needs to be implemented!")
    def test_is_installed(self):
        # todo: implement
        pass

    def test_get_solution_path(self):
        # call
        file = Path(
            self.solution_handler.get_solution_package_path(
                self.catalog, Coordinates("g", "n", "v")
            )
        ).resolve()
        self.assertEqual(
            get_link_target(
                self.catalog.path().joinpath(
                    DefaultValues.catalog_solutions_prefix.value, "g", "n", "v"
                )
            ).resolve(),
            file,
        )

    def test_get_solution_file(self):
        # call
        file = Path(
            self.solution_handler.get_solution_file(
                self.catalog, Coordinates("g", "n", "v")
            )
        ).resolve()
        res = get_link_target(
            self.catalog.path().joinpath(
                DefaultValues.catalog_solutions_prefix.value, "g", "n", "v"
            )
        ).joinpath("solution.py")
        self.assertEqual(res.resolve(), file)

    def test_get_solution_lock(self):
        # call
        lock = self.solution_handler.get_solution_lock(
            self.catalog, Coordinates("g", "n", "v")
        )

        # assert - a lock file per solution in the lock folder of the base path
        self.assertEqual(
            self.album_controller.configuration()
            .base_cache_path()
            .joinpath(
                DefaultValues.lock_folder_prefix.value, "test", "g", "n", "v.lock"
            ),
            lock._path,
        )
        # the same lock every time, which the thread holding it acquires again
        self.assertIs(
            lock,
            self.solution_handler.get_solution_lock(
                self.catalog, Coordinates("g", "n", "v")
            ),
        )
        with lock:
            with self.solution_handler.get_solution_lock(
                self.catalog, Coordinates("g", "n", "v")
            ):
                pass
        # another solution has another lock
        other_lock = self.solution_handler.get_solution_lock(
            self.catalog, Coordinates("g", "n", "v2")
        )
        self.assertNotEqual(lock._path, other_lock._path)

    def test_get_solution_zip_suffix(self):
        res = Path("").joinpath(
            DefaultValues.catalog_solutions_prefix.value, "g", "n", "v", "g_n_v.zip"
        )

        # call
        self.assertEqual(
            res,
            self.solution_handler.get_solution_zip_suffix(Coordinates("g", "n", "v")),
        )

    @patch(
        "album.core.controller.collection.solution_handler.SolutionHandler._download_solution"
    )
    def test_retrieve_solution(self, dl_mock):
        # prepare
        self.catalog = Catalog(
            catalog_id=self.catalog.catalog_id(),
            name=self.catalog.name(),
            path=str(self.catalog.path()),
            src="http://NonsenseUrl.git",
        )
        self.catalog.is_cache = MagicMock(return_value=False)
        get_solution_package_path = MagicMock(return_value=Path("somewhere"))
        self.solution_handler.get_solution_package_path = get_solution_package_path
        coordinates = Coordinates("g", "n", "v")

        # call
        solution_path = self.solution_handler.retrieve_solution(
            self.catalog, coordinates
        )

        # assert
        res = get_solution_package_path.return_value.joinpath(
            DefaultValues.solution_default_name.value
        )
        self.assertEqual(res.resolve(), solution_path.resolve())

        dl_mock.assert_called_once_with(
            "http://NonsenseUrl.git",
            coordinates,
            get_solution_package_path.return_value,
        )

    def test_set_cache_paths(self):
        config = self.album_controller.configuration()

        active_solution = Solution(self.solution_default_dict)
        path = self.album_controller.configuration().get_cache_path_catalog(
            "catalog_name_solution_lives_in"
        )
        catalog = Catalog(0, "catalog_name_solution_lives_in", path)
        self.solution_handler.set_cache_paths(active_solution, catalog)

        self.assertEqual(
            Path(config.lnk_path()).joinpath("pck", "0").resolve(),
            active_solution.installation().package_path().resolve(),
        )
        self.assertEqual(
            Path(config.lnk_path()).joinpath("inst", "0", "data").resolve(),
            active_solution.installation().data_path().resolve(),
        )
        self.assertEqual(
            Path(config.lnk_path()).joinpath("inst", "0", "app").resolve(),
            active_solution.installation().app_path().resolve(),
        )
        self.assertEqual(
            Path(config.lnk_path()).joinpath("inst", "0", "icache").resolve(),
            active_solution.installation().internal_cache_path().resolve(),
        )
        self.assertEqual(
            Path(config.lnk_path()).joinpath("inst", "0", "ucache").resolve(),
            active_solution.installation().user_cache_path().resolve(),
        )

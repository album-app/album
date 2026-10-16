import sys
import threading
import time
import unittest.mock
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from test.test_common import TEST_ALBUM_API_VERSION
from test.unit.test_unit_core_common import EmptyTestClass, TestUnitCoreCommon
from unittest.mock import ANY, MagicMock, call, patch

from album.core.api.model.catalog import ICatalog
from album.core.controller.album_controller import AlbumController
from album.core.controller.install_manager import InstallManager
from album.core.model.collection_index import CollectionIndex
from album.core.model.default_values import DefaultValues
from album.core.model.resolve_result import ResolveResult
from album.core.utils.file_lock import FileLock
from album.runner.core.model.coordinates import Coordinates
from album.runner.core.model.solution import Solution

# the solution of the tests, as set up by setup_solution_no_env()
SOLUTION = Coordinates("tsg", "tsn", "tsv")


def lock_path(
    album_controller: AlbumController, catalog: ICatalog, coordinates: Coordinates
) -> Path:
    return (
        album_controller.configuration()
        .base_cache_path()
        .joinpath(
            DefaultValues.lock_folder_prefix.value,
            catalog.name(),
            coordinates.group(),
            coordinates.name(),
            "%s.lock" % coordinates.version(),
        )
    )


def lock_of_other_process(
    album_controller: AlbumController, catalog: ICatalog, coordinates: Coordinates
) -> FileLock:
    # what another album process using the same base path holds while it installs
    # or uninstalls the solution
    return FileLock(
        lock_path(album_controller, catalog, coordinates),
        timeout=0,
        description="testing",
    )


def lock_is_free(
    album_controller: AlbumController, catalog: ICatalog, coordinates: Coordinates
) -> bool:
    # as seen by another album process using the same base path
    lock = lock_of_other_process(album_controller, catalog, coordinates)
    if not lock.acquire(blocking=False):
        return False
    lock.release()
    return True


class TestInstallManager(TestUnitCoreCommon):
    def setUp(self):
        super().setUp()
        self.setup_collection()
        self.setup_solution_no_env()
        self.install_manager: InstallManager = self.album_controller.install_manager()
        self.environment_manager = self.album_controller.environment_manager()
        self.catalog = (
            self.album_controller.collection_manager().catalogs().get_cache_catalog()
        )
        # waiting for the lock of the solution fails the test after 0.2 s instead of
        # after two hours
        self._solution_lock()._timeout = 0.2
        self.assertEqual(self.album_controller, self.install_manager.album)

    def tearDown(self) -> None:
        super().tearDown()

    def _solution_lock(self, coordinates: Coordinates = SOLUTION) -> FileLock:
        # the lock of the solution held by this album instance
        return self.album_controller.solutions().get_solution_lock(
            self.catalog, coordinates
        )

    def _lock_of_other_process(self, coordinates: Coordinates = SOLUTION) -> FileLock:
        return lock_of_other_process(self.album_controller, self.catalog, coordinates)

    def _lock_is_free(self, coordinates: Coordinates = SOLUTION) -> bool:
        return lock_is_free(self.album_controller, self.catalog, coordinates)

    def test_install(self):
        # create mocks
        resolve_result = ResolveResult(
            path=Path("aPath"),
            catalog=self.album_controller.collection_manager()
            .catalogs()
            .get_cache_catalog(),
            loaded_solution=self.active_solution,
            collection_entry=None,
            coordinates=self.active_solution.coordinates(),
        )

        _install_resolve_result = MagicMock(return_value=None)
        self.install_manager._install_loaded_resolve_result = _install_resolve_result

        resolve = MagicMock(return_value=resolve_result)
        self.album_controller.collection_manager().resolve_and_load = resolve

        # call
        self.install_manager.install("aPath", False, [])

        # assert
        _install_resolve_result.assert_called_once_with(
            resolve_result, parent=False, allow_recursive=False
        )

    @unittest.skip("Needs to be implemented!")
    def test__resolve_result_is_installed(self):
        # TODO implement
        pass

    def _prepare_install_loaded_resolve_result(
        self, installed, catalog=True, path: Path = None, single_file=False
    ):
        if path is None:
            path = Path(self.tmp_dir.name).joinpath("solution.py")
            path.touch()
        resolve_result = ResolveResult(
            path=path,
            catalog=(
                self.album_controller.collection_manager()
                .catalogs()
                .get_cache_catalog()
                if catalog
                else None
            ),
            loaded_solution=self.active_solution,
            collection_entry=None,
            coordinates=self.active_solution.coordinates(),
            single_file_solution=single_file,
        )

        # mocks
        self.is_installed = MagicMock(return_value=installed)
        self.install_manager._resolve_result_is_installed = self.is_installed

        self.clean_unfinished_installation = MagicMock()
        self.install_manager._clean_unfinished_installation = (
            self.clean_unfinished_installation
        )

        self.register = MagicMock()
        self.install_manager._register = self.register

        self.install_active_solution = MagicMock()
        self.install_manager._install_active_solution = self.install_active_solution

        self.set_installation_unfinished = MagicMock()
        self.album_controller.solutions().set_installation_unfinished = (
            self.set_installation_unfinished
        )

        self.set_installed = MagicMock()
        self.album_controller.solutions().set_installed = self.set_installed

        self.download_resources = MagicMock()
        self.album_controller.download_manager().download_resources = (
            self.download_resources
        )

        return resolve_result

    @patch("album.core.controller.install_manager.clean_resolve_tmp")
    def test__install_loaded_resolve_result(self, clean_resolve_tmp):
        r = self._prepare_install_loaded_resolve_result(installed=False)

        # call
        self.install_manager._install_loaded_resolve_result(r)

        # assert - checked before waiting for the lock and again holding it
        self.assertEqual([call(r), call(r)], self.is_installed.call_args_list)
        self.clean_unfinished_installation.assert_called_once_with(
            r.catalog(), r.coordinates()
        )
        self.register.assert_called_once_with(r)
        clean_resolve_tmp.assert_called_once()  # cache catalog
        self.set_installation_unfinished.assert_called_once_with(
            r.catalog(), r.coordinates()
        )
        self.download_resources.assert_called_once_with(r)
        self.install_active_solution.assert_called_once_with(r, ANY, False)
        self.set_installed.assert_called_once_with(r.catalog(), r.coordinates())
        self.assertIn('Installing "tsn"...', self.get_logs_as_string())

    @patch("album.core.controller.install_manager.clean_resolve_tmp")
    def test__install_loaded_resolve_result_parent(self, clean_resolve_tmp):
        r = self._prepare_install_loaded_resolve_result(installed=False)

        # call
        self.install_manager._install_loaded_resolve_result(r, parent=True)

        # assert
        self.assertEqual([call(r), call(r)], self.is_installed.call_args_list)
        self.register.assert_called_once_with(r)
        clean_resolve_tmp.assert_not_called()  # only cleaned for the child
        # a parent gets its resources, too
        self.download_resources.assert_called_once_with(r)
        self.install_active_solution.assert_called_once_with(r, ANY, False)
        self.set_installed.assert_called_once_with(r.catalog(), r.coordinates())
        self.assertIn('Installing parent solution "tsn"...', self.get_logs_as_string())

    def _solution_folder_with_environment_file(self):
        folder = Path(self.tmp_dir.name).joinpath("my-solution")
        folder.mkdir()
        folder.joinpath("solution.py").touch()
        folder.joinpath("environment.yml").write_text("dependencies:\n  - python\n")
        self.active_solution.setup().dependencies = {
            "environment_file": "environment.yml"
        }
        return folder

    @patch("album.core.controller.install_manager.clean_resolve_tmp")
    def test__install_loaded_resolve_result_single_file(self, _):
        self.active_solution.setup().dependencies = {
            "environment_file": "dependencies:\n  - python\n"
        }
        r = self._prepare_install_loaded_resolve_result(
            installed=False, single_file=True
        )

        # call
        self.install_manager._install_loaded_resolve_result(r)

        # assert
        self.register.assert_called_once_with(r)
        self.set_installed.assert_called_once_with(r.catalog(), r.coordinates())

    @patch("album.core.controller.install_manager.clean_resolve_tmp")
    def test__install_loaded_resolve_result_environment_file_in_folder(self, _):
        folder = self._solution_folder_with_environment_file()
        r = self._prepare_install_loaded_resolve_result(
            installed=False, path=folder.joinpath("solution.py")
        )

        # call
        self.install_manager._install_loaded_resolve_result(r)

        # assert
        self.register.assert_called_once_with(r)
        self.set_installed.assert_called_once_with(r.catalog(), r.coordinates())

    def test__install_loaded_resolve_result_environment_file_missing(self):
        folder = self._solution_folder_with_environment_file()
        folder.joinpath("environment.yml").unlink()
        r = self._prepare_install_loaded_resolve_result(
            installed=False, path=folder.joinpath("solution.py")
        )

        # call
        with self.assertRaises(TypeError) as e:
            self.install_manager._install_loaded_resolve_result(r)

        # assert: aborted before the solution is registered
        self.assertIn(
            'environment_file "environment.yml" does not exist',
            str(e.exception),
        )
        self.register.assert_not_called()
        self.set_installation_unfinished.assert_not_called()

    def test__install_loaded_resolve_result_single_file_with_environment_file(self):
        folder = self._solution_folder_with_environment_file()
        r = self._prepare_install_loaded_resolve_result(
            installed=False, path=folder.joinpath("solution.py"), single_file=True
        )

        # call: only solution.py would be installed, without the environment file
        with self.assertRaises(TypeError) as e:
            self.install_manager._install_loaded_resolve_result(r)

        # assert: aborted before the solution is registered
        self.assertIn(
            "is a path, so the solution has to be installed and deployed as a folder",
            str(e.exception),
        )
        self.register.assert_not_called()
        self.set_installation_unfinished.assert_not_called()

    @patch("album.core.controller.install_manager.clean_resolve_tmp")
    def test__install_loaded_resolve_result_files_written_by_deploy(self, _):
        # a deployed solution: the files it names are not on this computer, it is
        # installed from what album deploy wrote next to it
        folder = Path(self.tmp_dir.name).joinpath("my-solution")
        folder.mkdir()
        folder.joinpath("solution.py").touch()
        folder.joinpath("solution.environment.yml").write_text("dependencies: []\n")
        folder.joinpath("solution.resources.yml").write_text("resources: {}\n")
        self.active_solution.setup().dependencies = {
            "environment_file": "/not/on/this/computer/environment.yml",
            "resource_file": "resources.yml",
        }
        r = self._prepare_install_loaded_resolve_result(
            installed=False, path=folder.joinpath("solution.py")
        )

        # call
        self.install_manager._install_loaded_resolve_result(r)

        # assert
        self.register.assert_called_once_with(r)
        self.set_installed.assert_called_once_with(r.catalog(), r.coordinates())

    @patch("album.core.controller.install_manager.clean_resolve_tmp")
    def test__install_loaded_resolve_result_shows_replicability_reasons(self, _):
        # deployed with --no-replicability: album deploy stored the reasons
        folder = Path(self.tmp_dir.name).joinpath("deployed")
        folder.mkdir()
        folder.joinpath("solution.py").touch()
        folder.joinpath("solution.yml").write_text(
            'replicability:\n  reasons:\n  - resource "a" has no hash\n'
        )
        r = self._prepare_install_loaded_resolve_result(
            installed=False, path=folder.joinpath("solution.py")
        )

        # call
        self.install_manager._install_loaded_resolve_result(r)

        # assert
        self.assertIn(
            'Not technically replicable, "tsg:tsn:tsv": resource "a" has no hash',
            self.get_logs_as_string(),
        )
        self.set_installed.assert_called_once()

    def test_install_from_url(self):
        self.install_manager.clean_unfinished_installations = MagicMock()
        self.album_controller.collection_manager().resolve_and_load = MagicMock()
        self.install_manager._install_loaded_resolve_result = MagicMock()

        # call
        self.install_manager.install("https://example.org/solution.py")

        # assert
        self.assertIn(
            'Not technically replicable, "https://example.org/solution.py": it is '
            "installed from a url, whose content can change.",
            self.get_logs_as_string(),
        )

    @patch("album.core.controller.install_manager.clean_resolve_tmp")
    def test__install_loaded_resolve_result_resources_before_environment(self, _):
        r = self._prepare_install_loaded_resolve_result(installed=False)
        lock_free = []

        def download_resources(resolve_result):
            # marked unfinished and holding the lock, before the environment is built
            self.set_installation_unfinished.assert_called_once()
            self.install_active_solution.assert_not_called()
            lock_free.append(self._lock_is_free())

        self.download_resources.side_effect = download_resources

        # call
        self.install_manager._install_loaded_resolve_result(r)

        # assert
        self.download_resources.assert_called_once_with(r)
        self.assertEqual([False], lock_free)
        self.set_installed.assert_called_once_with(r.catalog(), r.coordinates())

    @patch("album.core.controller.install_manager.clean_resolve_tmp")
    def test__install_loaded_resolve_result_resources_fail(self, _):
        r = self._prepare_install_loaded_resolve_result(installed=False)
        error = RuntimeError('Could not retrieve resource "a"')
        self.download_resources.side_effect = error

        # call
        with self.assertRaises(RuntimeError) as context:
            self.install_manager._install_loaded_resolve_result(r)

        # assert - no environment, the failed installation is removed right away
        self.assertIs(error, context.exception)
        self.install_active_solution.assert_not_called()
        self.set_installed.assert_not_called()
        self.assertEqual(2, self.clean_unfinished_installation.call_count)
        self.assertTrue(self._lock_is_free())

    @patch("album.core.controller.install_manager.clean_resolve_tmp")
    def test__install_loaded_resolve_result_holds_lock(self, _):
        r = self._prepare_install_loaded_resolve_result(installed=False)
        lock_free = []
        for step in [
            self.clean_unfinished_installation,
            self.register,
            self.install_active_solution,
            self.set_installed,
        ]:
            step.side_effect = lambda *args: lock_free.append(self._lock_is_free())

        # call
        self.install_manager._install_loaded_resolve_result(r)

        # assert
        self.assertEqual([False, False, False, False], lock_free)
        self.assertTrue(self._lock_is_free())

    def test__install_loaded_resolve_result_releases_lock_on_failure(self):
        r = self._prepare_install_loaded_resolve_result(installed=False)
        self.install_active_solution.side_effect = RuntimeError("Installation failed!")

        # call
        with self.assertRaises(RuntimeError):
            self.install_manager._install_loaded_resolve_result(r)

        # assert
        self.assertTrue(self._lock_is_free())

    def test__install_loaded_resolve_result_removes_failed_installation(self):
        r = self._prepare_install_loaded_resolve_result(installed=False)
        error = RuntimeError("Installation failed!")
        self.install_active_solution.side_effect = error
        lock_free = []
        self.clean_unfinished_installation.side_effect = lambda *args: (
            lock_free.append(self._lock_is_free())
        )

        # call
        with self.assertRaises(RuntimeError) as context:
            self.install_manager._install_loaded_resolve_result(r)

        # assert - a leftover is removed before installing, the failed installation
        # right after it failed, both holding the lock
        self.assertIs(error, context.exception)
        self.assertEqual(
            [call(r.catalog(), r.coordinates()), call(r.catalog(), r.coordinates())],
            self.clean_unfinished_installation.call_args_list,
        )
        self.assertEqual([False, False], lock_free)
        self.set_installed.assert_not_called()
        self.assertTrue(self._lock_is_free())

    def test__install_loaded_resolve_result_interrupted(self):
        r = self._prepare_install_loaded_resolve_result(installed=False)
        self.install_active_solution.side_effect = KeyboardInterrupt()

        # call
        with self.assertRaises(KeyboardInterrupt):
            self.install_manager._install_loaded_resolve_result(r)

        # assert - removed as well
        self.assertEqual(2, self.clean_unfinished_installation.call_count)
        self.assertTrue(self._lock_is_free())

    def test__install_loaded_resolve_result_not_marked_installed(self):
        r = self._prepare_install_loaded_resolve_result(installed=False)
        self.set_installed.side_effect = RuntimeError("Database is locked!")

        # call
        with self.assertRaises(RuntimeError):
            self.install_manager._install_loaded_resolve_result(r)

        # assert - not left installed but marked unfinished
        self.assertEqual(2, self.clean_unfinished_installation.call_count)

    def test__install_loaded_resolve_result_failed_installation_not_removed(self):
        r = self._prepare_install_loaded_resolve_result(installed=False)
        self.install_active_solution.side_effect = RuntimeError("Installation failed!")
        # the failed installation cannot be removed
        self.clean_unfinished_installation.side_effect = [None, PermissionError("busy")]

        # call - raises the error of the installation
        with self.assertRaisesRegex(RuntimeError, "Installation failed!"):
            self.install_manager._install_loaded_resolve_result(r)

        # assert - it stays marked unfinished, the next installation removes it
        self.assertIn(
            'Cannot remove the unfinished installation of "tsg:tsn:tsv": busy',
            self.get_logs_as_string(),
        )
        self.assertTrue(self._lock_is_free())

    def test__install_loaded_resolve_result_waits_for_other_process(self):
        r = self._prepare_install_loaded_resolve_result(installed=False)

        # another album process using the same base path installs the solution
        with self._lock_of_other_process():
            # call
            with self.assertRaises(TimeoutError):
                self.install_manager._install_loaded_resolve_result(r)

        # assert - its installation in progress is not touched
        self.clean_unfinished_installation.assert_not_called()
        self.register.assert_not_called()
        self.install_active_solution.assert_not_called()
        self.assertIn(
            "Waiting for another album process or thread to finish installing or "
            'uninstalling "%s:tsg:tsn:tsv" or a solution depending on it'
            % self.catalog.name(),
            self.get_logs_as_string(),
        )

    @patch("album.core.controller.install_manager.clean_resolve_tmp")
    def test__install_loaded_resolve_result_other_solution_locked(self, _):
        r = self._prepare_install_loaded_resolve_result(installed=False)

        # another album process using the same base path installs another solution
        with self._lock_of_other_process(Coordinates("tsg", "other", "tsv")):
            # call
            self.install_manager._install_loaded_resolve_result(r)

        # assert - installed without waiting
        self.install_active_solution.assert_called_once()
        self.set_installed.assert_called_once_with(r.catalog(), r.coordinates())
        self.assertNotIn("Waiting", self.get_logs_as_string())

    def test__install_loaded_resolve_result_installed_while_waiting(self):
        r = self._prepare_install_loaded_resolve_result(installed=False)
        # another album process installed it while this one waited for the lock
        self.is_installed.side_effect = [False, True]

        # call
        self.install_manager._install_loaded_resolve_result(r)

        # assert
        self.clean_unfinished_installation.assert_not_called()
        self.register.assert_not_called()
        self.install_active_solution.assert_not_called()
        self.assertIn(
            'Solution "tsn" already installed. Skipping...', self.get_logs_as_string()
        )

    @patch("album.core.controller.install_manager.clean_resolve_tmp")
    def test__install_loaded_resolve_result_solution_files_removed(self, _):
        # e.g. by another album process that failed to install the solution while
        # this one waited for the lock, or with an unfinished installation
        r = self._prepare_install_loaded_resolve_result(
            installed=False, path=Path(self.tmp_dir.name).joinpath("gone.py")
        )
        retrieve_and_load_resolve_result = MagicMock()
        self.album_controller.collection_manager().retrieve_and_load_resolve_result = (
            retrieve_and_load_resolve_result
        )
        set_cache_paths = MagicMock()
        self.album_controller.solutions().set_cache_paths = set_cache_paths

        # call
        self.install_manager._install_loaded_resolve_result(r)

        # assert - retrieved and loaded again
        retrieve_and_load_resolve_result.assert_called_once_with(r)
        set_cache_paths.assert_called_once_with(r.loaded_solution(), r.catalog())
        self.install_active_solution.assert_called_once()

    def test__install_loaded_resolve_result_already_installed(self):
        r = self._prepare_install_loaded_resolve_result(installed=True)

        # call: skipped with a warning, does not raise
        self.install_manager._install_loaded_resolve_result(r)

        # assert
        self.is_installed.assert_called_once_with(r)
        self.register.assert_not_called()
        self.download_resources.assert_not_called()
        self.install_active_solution.assert_not_called()
        self.set_installed.assert_not_called()
        self.assertIn(
            'Solution "tsn" already installed. Skipping...', self.get_logs_as_string()
        )

    def test__install_loaded_resolve_result_parent_already_installed(self):
        r = self._prepare_install_loaded_resolve_result(installed=True)

        # call: skipped silently
        self.install_manager._install_loaded_resolve_result(r, parent=True)

        # assert
        self.is_installed.assert_called_once_with(r)
        self.register.assert_not_called()
        self.install_active_solution.assert_not_called()
        self.set_installed.assert_not_called()
        self.assertNotIn("already installed", self.get_logs_as_string())

    def test__install_loaded_resolve_result_no_catalog(self):
        r = self._prepare_install_loaded_resolve_result(installed=False, catalog=False)

        # call
        with self.assertRaises(RuntimeError):
            self.install_manager._install_loaded_resolve_result(r)

        # assert
        self.is_installed.assert_not_called()
        self.register.assert_not_called()

    @unittest.skip("Needs to be implemented!")
    def test__register(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_set_parent(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_update_in_collection_index(self):
        # TODO implement
        pass

    def test__install_active_solution(self):
        self.active_solution.environment = EmptyTestClass()

        # mocks
        user_cache_path = MagicMock(return_value=Path(self.tmp_dir.name))
        self.active_solution.installation().user_cache_path = user_cache_path

        internal_cache_path = MagicMock(return_value=Path(self.tmp_dir.name))
        self.active_solution.installation().internal_cache_path = internal_cache_path

        package_path = MagicMock(return_value=Path(self.tmp_dir.name))
        self.active_solution.installation().app_path = package_path

        data_path = MagicMock(return_value=Path(self.tmp_dir.name))
        self.active_solution.installation().data_path = data_path

        install_environment = MagicMock(return_value=None)
        self.environment_manager.install_environment = install_environment

        set_environment = MagicMock(return_value=None)
        self.environment_manager.set_environment = set_environment

        run_solution_install_routine = MagicMock()
        self.install_manager._run_solution_install_routine = (
            run_solution_install_routine
        )

        r = ResolveResult(
            path=Path(""),
            catalog=self.album_controller.collection_manager()
            .catalogs()
            .get_cache_catalog(),
            collection_entry=None,
            coordinates=self.active_solution.coordinates(),
            loaded_solution=self.active_solution,
        )

        # call
        self.install_manager._install_active_solution(r, ExitStack())

        # assert
        run_solution_install_routine.assert_called_once_with(r)
        set_environment.assert_not_called()
        install_environment.assert_called_once()
        user_cache_path.assert_called_once()
        internal_cache_path.assert_called_once()
        package_path.assert_called_once()
        data_path.assert_called_once()

    def test__install_active_solution_with_parent(self):
        self.active_solution._setup.album_api_version = "1.0.1"

        self.parent_solution = Solution(deepcopy(dict(self.active_solution.setup())))
        self.parent_solution.environment = (
            lambda: EmptyTestClass()
        )  # different object in memory

        self.active_solution._setup.dependencies = {"parent": "aParent"}

        # mocks
        user_cache_path = MagicMock(return_value=Path(self.tmp_dir.name))
        self.active_solution.installation().user_cache_path = user_cache_path

        internal_cache_path = MagicMock(return_value=Path(self.tmp_dir.name))
        self.active_solution.installation().internal_cache_path = internal_cache_path

        package_path = MagicMock(return_value=Path(self.tmp_dir.name))
        self.active_solution.installation().app_path = package_path

        data_path = MagicMock(return_value=Path(self.tmp_dir.name))
        self.active_solution.installation().data_path = data_path

        install_environment = MagicMock(return_value=None)
        self.environment_manager.install_environment = install_environment

        parent_resolve_result = ResolveResult(
            Path(""),
            None,
            CollectionIndex.CollectionSolution(),
            None,
            loaded_solution=self.parent_solution,
        )
        _install_parent = MagicMock(return_value=parent_resolve_result)
        self.install_manager._install_parent = _install_parent

        self.album_controller.solutions().set_parent = MagicMock()

        run_solution_install_routine = MagicMock()
        self.install_manager._run_solution_install_routine = (
            run_solution_install_routine
        )

        self.album_controller.collection_manager().get_collection_index().get_solution_by_catalog_grp_name_version = MagicMock(
            return_value=CollectionIndex.CollectionSolution()
        )

        r = ResolveResult(
            Path(""),
            self.album_controller.collection_manager().catalogs().get_cache_catalog(),
            CollectionIndex.CollectionSolution(),
            self.active_solution.coordinates(),
            self.active_solution,
        )

        # call
        locks = ExitStack()
        self.install_manager._install_active_solution(r, locks)

        # assert
        _install_parent.assert_called_once_with(
            "aParent",
            "1.0.1",
            Coordinates("tsg", "tsn", "tsv"),
            locks,
            allow_recursive=False,
            catalog=r.catalog(),
        )
        run_solution_install_routine.assert_called_once_with(r)
        install_environment.assert_not_called()

        user_cache_path.assert_called_once()
        internal_cache_path.assert_called_once()
        package_path.assert_called_once()
        data_path.assert_called_once()

        # the solution runs in the environment of its parent, the flag goes there
        _install_parent.reset_mock()
        self.install_manager._install_active_solution(r, locks, allow_recursive=True)
        _install_parent.assert_called_once_with(
            "aParent",
            "1.0.1",
            Coordinates("tsg", "tsn", "tsv"),
            locks,
            allow_recursive=True,
            catalog=r.catalog(),
        )

    @unittest.skip("Needs to be implemented!")
    def test_run_solution_install_routine(self):
        # TODO implement
        pass

    def _prepare_install_parent(self, catalog=True) -> ResolveResult:
        self.parent_coordinates = Coordinates("myGroup", "myName", "myVersion")
        s = Solution(
            {
                "group": "myGroup",
                "name": "myName",
                "version": "myVersion",
            }
        )

        class R:
            album_api_version = "5.1.0"

        s._setup = R()
        r = ResolveResult(
            "", self.catalog if catalog else None, None, self.parent_coordinates, s
        )

        # mocks
        self.install_holding_lock = MagicMock(return_value=None)
        self.install_manager._install_holding_lock = self.install_holding_lock

        self.resolve_and_load = MagicMock(return_value=r)
        self.album_controller.collection_manager().resolve_and_load = (
            self.resolve_and_load
        )
        return r

    @patch(
        "album.core.controller.install_manager.build_resolve_string",
        return_value="myResolveString",
    )
    def test__install_parent(self, build_resolve_string_mock):
        r = self._prepare_install_parent()
        lock_free_during_install = []
        self.install_holding_lock.side_effect = lambda *args, **kwargs: (
            lock_free_during_install.append(self._lock_is_free(r.coordinates()))
        )

        # call
        with ExitStack() as locks:
            self.install_manager._install_parent(
                {"myDictKey": "myDeps"}, "5.1.0", Coordinates("a", "b", "c"), locks
            )

            # assert - the parent stays locked until the child is installed into its
            # environment, the locks are then released
            self.assertFalse(self._lock_is_free(r.coordinates()))
        self.assertTrue(self._lock_is_free(r.coordinates()))

        # asert
        self.install_holding_lock.assert_called_once_with(
            r, parent=True, allow_recursive=False, locks=locks
        )
        self.assertEqual([False], lock_free_during_install)
        self.resolve_and_load.assert_called_once()
        build_resolve_string_mock.assert_called_once_with({"myDictKey": "myDeps"})

        # allow_recursive reaches the installation of the parent
        self.install_holding_lock.reset_mock()
        with ExitStack() as locks:
            self.install_manager._install_parent(
                {"myDictKey": "myDeps"},
                "5.1.0",
                Coordinates("a", "b", "c"),
                locks,
                allow_recursive=True,
            )
        self.install_holding_lock.assert_called_once_with(
            r, parent=True, allow_recursive=True, locks=locks
        )

    @patch(
        "album.core.controller.install_manager.build_resolve_string",
        return_value="myResolveString",
    )
    def test__install_parent_waits_for_other_process(self, _):
        r = self._prepare_install_parent()
        self._solution_lock(r.coordinates())._timeout = 0.2

        # another album process installs the parent, or another child of it
        with self._lock_of_other_process(r.coordinates()):
            # call
            with ExitStack() as locks:
                with self.assertRaises(TimeoutError):
                    self.install_manager._install_parent(
                        {"myDictKey": "myDeps"},
                        "5.1.0",
                        Coordinates("a", "b", "c"),
                        locks,
                    )

        # assert
        self.install_holding_lock.assert_not_called()

    @patch(
        "album.core.controller.install_manager.build_resolve_string",
        return_value="myResolveString",
    )
    def test__install_parent_own_parent(self, _):
        # the parent is a child of the solution being installed, e.g. the parent of
        # its parent
        r = self._prepare_install_parent()

        with ExitStack() as locks:
            locks.enter_context(self._solution_lock(r.coordinates()))
            # call
            with self.assertRaises(ValueError):
                self.install_manager._install_parent(
                    {"myDictKey": "myDeps"}, "5.1.0", Coordinates("a", "b", "c"), locks
                )

        # assert
        self.install_holding_lock.assert_not_called()
        self.assertTrue(self._lock_is_free(r.coordinates()))

    @patch(
        "album.core.controller.install_manager.build_resolve_string",
        return_value="myResolveString",
    )
    def test__install_parent_eq_child(self, build_resolve_string_mock):
        r = self._prepare_install_parent(catalog=False)

        # call
        with self.assertRaises(ValueError):
            self.install_manager._install_parent(
                {"myDictKey": "myDeps"}, "5.1.0", r.coordinates(), ExitStack()
            )

        # assert
        self.install_holding_lock.assert_not_called()

    def test__resolve_parent(self):
        collection_manager = self.album_controller.collection_manager()
        collection_manager.resolve_and_load_catalog_coordinates = MagicMock(
            return_value="from its catalog"
        )
        collection_manager.resolve_and_load = MagicMock(return_value="found first")
        catalog = MagicMock()
        catalog.is_cache.return_value = False
        catalog.name.return_value = "cat"
        parent = {"group": "gp", "name": "np", "version": "vp"}
        child = Coordinates("g", "n", "v")

        # in the catalog of the solution
        self.assertEqual(
            "from its catalog",
            self.install_manager._resolve_parent(parent, child, catalog),
        )
        collection_manager.resolve_and_load_catalog_coordinates.assert_called_once_with(
            catalog, Coordinates("gp", "np", "vp")
        )
        collection_manager.resolve_and_load.assert_not_called()

        # not in it: the one album finds first
        collection_manager.resolve_and_load_catalog_coordinates.side_effect = (
            LookupError()
        )
        self.assertEqual(
            "found first", self.install_manager._resolve_parent(parent, child, catalog)
        )
        collection_manager.resolve_and_load.assert_called_once_with("gp:np:vp")
        self.assertIn(
            'Not technically replicable, "g:n:v": its parent "gp:np:vp" is not in its '
            'catalog "cat", album takes the one it finds first.',
            self.get_logs_as_string(),
        )

        # a solution installed from a file, a parent given by its DOI: as before
        cache_catalog = MagicMock()
        cache_catalog.is_cache.return_value = True
        for parent_dict, solution_catalog, resolved in [
            (parent, cache_catalog, "gp:np:vp"),
            ({"doi": "10.5281/zenodo.123"}, catalog, "10.5281/zenodo.123"),
            (parent, None, "gp:np:vp"),
        ]:
            with self.subTest(parent=parent_dict, catalog=solution_catalog):
                collection_manager.resolve_and_load.reset_mock()
                self.install_manager._resolve_parent(
                    parent_dict, child, solution_catalog
                )
                collection_manager.resolve_and_load.assert_called_once_with(resolved)

    @unittest.skip("Needs to be implemented!")
    def test_uninstall(self):
        # TODO implement
        pass

    def _prepare_uninstall(self, load_error=None, parent=None, children=None):
        # an installed solution as it is stored in the collection
        collection_entry = CollectionIndex.CollectionSolution(
            {"group": "tsg", "name": "tsn", "version": "tsv"},  # setup
            {"parent": parent, "children": children or []},  # internal
        )
        resolve_result = ResolveResult(
            path=Path(self.tmp_dir.name).joinpath("solution.py"),
            catalog=self.album_controller.collection_manager()
            .catalogs()
            .get_cache_catalog(),
            collection_entry=collection_entry,
            coordinates=Coordinates("tsg", "tsn", "tsv"),
        )

        # mocks
        self.resolve_installed = MagicMock(return_value=resolve_result)
        self.album_controller.collection_manager().resolve_installed = (
            self.resolve_installed
        )

        # without a load error the solution file loads, here a no-op
        self.load_resolve_result = MagicMock(side_effect=load_error)
        self.album_controller.collection_manager().load_resolve_result = (
            self.load_resolve_result
        )

        self.set_environment = MagicMock(return_value="myEnv")
        self.environment_manager.set_environment = self.set_environment

        self.remove_environment = MagicMock(return_value=True)
        self.environment_manager.remove_environment = self.remove_environment

        self.run_solution_uninstall_routine = MagicMock()
        self.install_manager._run_solution_uninstall_routine = (
            self.run_solution_uninstall_routine
        )

        self.remove_solution = MagicMock()
        self.album_controller.solutions().remove_solution = self.remove_solution

        self.install_manager._remove_disc_content_from_solution = MagicMock()

        return resolve_result

    @patch(
        "album.core.controller.install_manager.EnvironmentManager.remove_disc_content_from_environment"
    )
    def test_uninstall_loaded(self, remove_disc_content_from_environment):
        r = self._prepare_uninstall()

        # call
        self.install_manager.uninstall("tsg:tsn:tsv")

        # assert
        # looked up to know which solution to lock, and again holding the lock
        self.assertEqual(
            [call("tsg:tsn:tsv")] * 2, self.resolve_installed.call_args_list
        )
        self.load_resolve_result.assert_called_once_with(r)
        self.set_environment.assert_called_once_with(r)
        self.run_solution_uninstall_routine.assert_called_once_with(r)
        self.remove_environment.assert_called_once_with("myEnv")
        remove_disc_content_from_environment.assert_called_once_with("myEnv")
        self.remove_solution.assert_called_once_with(r.catalog(), r.coordinates())
        self.assertNotIn("Cannot load solution", self.get_logs_as_string())

    def test_uninstall_not_installed_or_not_found(self):
        # the lookup fails: nothing to uninstall, the caller gets that error right away
        for lookup_error in [
            ValueError("Solution seems not to be installed!"),
            LookupError("Cannot find solution tsg:tsn:tsv!"),
        ]:
            with self.subTest(lookup_error=type(lookup_error).__name__):
                self._prepare_uninstall()
                self.resolve_installed.side_effect = lookup_error

                # call
                with self.assertRaises(type(lookup_error)) as context:
                    self.install_manager.uninstall("tsg:tsn:tsv")

                # assert: not resolved a second time, no warning about loading
                self.assertIs(lookup_error, context.exception)
                self.resolve_installed.assert_called_once_with("tsg:tsn:tsv")
                self.load_resolve_result.assert_not_called()
                self.set_environment.assert_not_called()
                self.remove_solution.assert_not_called()
                self.assertNotIn("Cannot load solution", self.get_logs_as_string())

    @patch(
        "album.core.controller.install_manager.EnvironmentManager.remove_disc_content_from_environment"
    )
    def test_uninstall_holds_lock(self, _):
        self._prepare_uninstall()
        lock_free_during_uninstall = []
        self.remove_solution.side_effect = lambda *args: (
            lock_free_during_uninstall.append(self._lock_is_free())
        )

        # call
        self.install_manager.uninstall("tsg:tsn:tsv")

        # assert
        self.assertEqual([False], lock_free_during_uninstall)
        self.assertTrue(self._lock_is_free())

    def test_uninstall_waits_for_other_process(self):
        self._prepare_uninstall()

        # another album process using the same base path installs or uninstalls it
        with self._lock_of_other_process():
            # call
            with self.assertRaises(TimeoutError):
                self.install_manager.uninstall("tsg:tsn:tsv")

        # assert
        self.remove_environment.assert_not_called()
        self.remove_solution.assert_not_called()

    @patch(
        "album.core.controller.install_manager.EnvironmentManager.remove_disc_content_from_environment"
    )
    def test_uninstall_other_solution_locked(self, _):
        self._prepare_uninstall()

        # another album process using the same base path installs another solution
        with self._lock_of_other_process(Coordinates("tsg", "other", "tsv")):
            # call
            self.install_manager.uninstall("tsg:tsn:tsv")

        # assert - uninstalled without waiting
        self.remove_solution.assert_called_once()
        self.assertNotIn("Waiting", self.get_logs_as_string())

    def test_uninstall_rm_dep_locks_child_and_parent(self):
        child = ResolveResult(
            Path("child"), self.catalog, None, Coordinates("tsg", "child", "tsv")
        )
        parent = ResolveResult(
            Path("parent"), self.catalog, None, Coordinates("tsg", "parent", "tsv")
        )
        self.album_controller.collection_manager().resolve_installed = MagicMock(
            side_effect=lambda solution_to_resolve: (
                child if solution_to_resolve == "child" else parent
            )
        )
        locks_free = {}

        def _uninstall(solution_to_resolve, rm_dep, as_dependency):
            locks_free[solution_to_resolve] = (
                self._lock_is_free(child.coordinates()),
                self._lock_is_free(parent.coordinates()),
            )
            if solution_to_resolve == "child":
                # removing the parent is a recursive uninstall call
                self.install_manager._uninstall_parent("parent", rm_dep)

        self.install_manager._uninstall = _uninstall

        # call
        self.install_manager.uninstall("child", True)

        # assert - the child stays locked while its parent is uninstalled
        self.assertEqual({"child": (False, True), "parent": (False, False)}, locks_free)
        self.assertTrue(self._lock_is_free(child.coordinates()))
        self.assertTrue(self._lock_is_free(parent.coordinates()))

    @patch(
        "album.core.controller.install_manager.EnvironmentManager.remove_disc_content_from_environment"
    )
    def test_uninstall_solution_cannot_be_loaded(
        self, remove_disc_content_from_environment
    ):
        # no setup() call in the file, file missing, file broken
        for load_error in [
            ValueError("Cannot load solution!"),
            FileNotFoundError("solution.py"),
            SyntaxError("invalid syntax"),
        ]:
            with self.subTest(load_error=type(load_error).__name__):
                remove_disc_content_from_environment.reset_mock()
                r = self._prepare_uninstall(load_error=load_error)

                # call
                self.install_manager.uninstall("tsg:tsn:tsv")

                # assert
                # looked up to know which solution to lock, and again holding the lock
                self.assertEqual(
                    [call("tsg:tsn:tsv")] * 2, self.resolve_installed.call_args_list
                )
                self.assertIn("Cannot load solution", self.get_logs_as_string())
                self.set_environment.assert_called_once_with(r)
                self.run_solution_uninstall_routine.assert_not_called()
                self.remove_environment.assert_called_once_with("myEnv")
                remove_disc_content_from_environment.assert_called_once_with("myEnv")
                self.remove_solution.assert_called_once_with(
                    r.catalog(), r.coordinates()
                )

    @patch(
        "album.core.controller.install_manager.EnvironmentManager.remove_disc_content_from_environment"
    )
    def test_uninstall_solution_cannot_be_loaded_parent(
        self, remove_disc_content_from_environment
    ):
        # the solution runs in the environment of its parent, which must be kept
        r = self._prepare_uninstall(
            load_error=ValueError("Cannot load solution!"),
            parent=CollectionIndex.CollectionSolution(),
        )

        # call
        self.install_manager.uninstall("tsg:tsn:tsv")

        # assert
        self.run_solution_uninstall_routine.assert_not_called()
        self.remove_environment.assert_not_called()
        remove_disc_content_from_environment.assert_not_called()
        self.remove_solution.assert_called_once_with(r.catalog(), r.coordinates())

    def test_upgrade_solutions_and_reinstall_hold_the_upgrade_lock(self):
        lock = self.album_controller.solutions().get_upgrade_lock()
        held = []
        self.install_manager._upgrade_solutions = lambda *args: held.append(
            lock.is_held_by_current_thread()
        )
        self.install_manager._reinstall = lambda *args: held.append(
            lock.is_held_by_current_thread()
        )

        # call
        self.install_manager.upgrade_solutions()
        self.install_manager.install("grp:name:0.1.0", reinstall=True)

        # assert
        self.assertEqual([True, True], held)
        self.assertFalse(lock.is_held_by_current_thread())

    @patch("album.core.controller.install_manager.check_file_or_url")
    def test__local_source_url(self, check_file_or_url):
        catalog = self.album_controller.catalogs().get_cache_catalog()
        coordinates = Coordinates("g", "n", "v")
        target = self.install_manager._staged(self.tmp_dir.name, catalog, coordinates)

        # downloaded now: a zip is unpacked into a folder
        check_file_or_url.return_value = target.joinpath("unpacked", "solution.py")
        self.assertEqual(
            str(target.joinpath("unpacked")),
            self.install_manager._local_source(
                "https://example.org/s.zip", catalog, coordinates, self.tmp_dir.name
            ),
        )

        # a single file stays one
        check_file_or_url.return_value = target.joinpath("tmp1234")
        self.assertEqual(
            str(target.joinpath("tmp1234")),
            self.install_manager._local_source(
                "https://example.org/s.py", catalog, coordinates, self.tmp_dir.name
            ),
        )
        check_file_or_url.assert_called_with("https://example.org/s.py", target)

    def test__load_staged(self):
        catalog = self.album_controller.catalogs().get_cache_catalog()
        coordinates = Coordinates("g", "n", "v")
        staged = self.install_manager._staged(self.tmp_dir.name, catalog, coordinates)
        staged.mkdir(parents=True)
        staged.joinpath("solution.py").write_text(
            "from album.runner.api import setup\n"
            "setup(group='g', name='n', version='v', album_api_version='%s')\n"
            % TEST_ALBUM_API_VERSION
        )

        r = self.install_manager._load_staged(self.tmp_dir.name, catalog, coordinates)

        # installed from the copy as a folder, with the files next to solution.py
        self.assertEqual(staged.joinpath("solution.py"), r.path())
        self.assertFalse(r.is_single_file())
        self.assertEqual("n", r.loaded_solution().coordinates().name())

    def test__check_files_to_install_again(self):
        catalog = self.album_controller.catalogs().get_cache_catalog()
        folder = Path(self.tmp_dir.name).joinpath("solution")
        folder.mkdir()
        folder.joinpath("environment.yml").write_text("dependencies: []\n")

        def to_install(environment_file):
            solution = Solution(
                dict(
                    self.get_solution_dict(),
                    dependencies={"environment_file": environment_file},
                )
            )
            return ResolveResult(
                path=folder.joinpath("solution.py"),
                catalog=catalog,
                collection_entry=None,
                coordinates=solution.coordinates(),
                loaded_solution=solution,
            )

        Path(self.tmp_dir.name).joinpath("shared.yml").write_text("dependencies: []\n")
        valid = to_install("environment.yml")
        missing = to_install("missing.yml")
        rule = 'environment_file "missing.yml" does not exist: there is no file %s.' % (
            folder.joinpath("missing.yml")
        )

        # existing files pass, also outside the folder of the solution
        self.install_manager._check_files_to_install_again(
            "cat:g:a:1", valid, [("cat:g:b:1", to_install("../shared.yml"))]
        )

        for solution, children, message in [
            (
                missing,
                [("cat:g:b:1", valid)],
                rule + ' Uninstall "cat:g:a:1" and install it by hand.',
            ),
            # a solution running in its environment is uninstalled with it
            (
                valid,
                [("cat:g:b:1", missing)],
                '"cat:g:b:1", which runs in its environment: '
                + rule
                + ' Uninstall "cat:g:b:1" and install it by hand.',
            ),
        ]:
            with self.subTest(message=message):
                with self.assertRaises(TypeError) as e:
                    self.install_manager._check_files_to_install_again(
                        "cat:g:a:1", solution, children
                    )
                self.assertEqual(message, str(e.exception))

    def test_uninstall_solution_other_solutions_run_in(self):
        # whether or not the solution has a parent itself
        for parent in [None, CollectionIndex.CollectionSolution()]:
            with self.subTest(has_parent=parent is not None):
                self._prepare_uninstall(
                    parent=parent, children=[{"collection_id_child": 2}]
                )
                self.install_manager._get_child_solution_coordinates = MagicMock(
                    return_value=[Coordinates("tsg", "child", "tsv")]
                )

                # asked for directly, it cannot be uninstalled
                with self.assertRaises(RuntimeError):
                    self.install_manager.uninstall("tsg:tsn:tsv")

                # as the parent of a solution uninstalled with its dependencies, it stays
                self.install_manager._uninstall_parent("tsg:tsn:tsv", True)

                self.assertIn(
                    "The following solutions depend on this installation: "
                    "tsg:child:tsv. Not uninstalling tsg:tsn:tsv",
                    self.get_logs_as_string(),
                )
                self.run_solution_uninstall_routine.assert_not_called()
                self.remove_environment.assert_not_called()
                self.remove_solution.assert_not_called()

    @unittest.skip("Needs to be implemented!")
    def test__uninstall(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_run_solution_uninstall_routine(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_remove_dependencies(self):
        # TODO implement
        pass

    @patch(
        "album.core.controller.install_manager.dict_to_coordinates",
        return_value=Coordinates("g1", "n1", "v1"),
    )
    def test_clean_unfinished_installations_env_exists(self, _):
        # mocks
        remove_dc = MagicMock()
        self.album_controller.install_manager()._remove_disc_content_from_solution = (
            remove_dc
        )

        set_cache_paths = MagicMock()
        self.album_controller.collection_manager().solutions().set_cache_paths = (
            set_cache_paths
        )
        entry = CollectionIndex.CollectionSolution(
            {"group": "g1", "name": "n1", "version": "v1"},  # setup
            {"catalog_id": 1, "parent": None, "installation_unfinished": 1},  # internal
        )
        get_unfinished_installation_solutions = MagicMock(return_value=[entry])
        self.album_controller.collection_manager().get_collection_index().get_unfinished_installation_solutions = (
            get_unfinished_installation_solutions
        )
        # looked up again holding the lock of the solution
        get_solution = MagicMock(return_value=entry)
        self.album_controller.collection_manager().get_collection_index().get_solution_by_catalog_grp_name_version = (
            get_solution
        )

        get_by_id_mock = MagicMock(
            return_value=self.album_controller.collection_manager()
            .catalogs()
            .get_cache_catalog()
        )
        self.album_controller.collection_manager().catalogs().get_by_id = get_by_id_mock

        retrieve_and_load_resolve_result = MagicMock()
        self.album_controller.collection_manager().retrieve_and_load_resolve_result = (
            retrieve_and_load_resolve_result
        )

        _clean_unfinished_installations_environment = MagicMock()
        self.install_manager._clean_unfinished_installations_environment = (
            _clean_unfinished_installations_environment
        )

        remove_solution = MagicMock()
        self.album_controller.collection_manager().solutions().remove_solution = (
            remove_solution
        )

        # call
        self.install_manager.clean_unfinished_installations()

        # assert
        get_solution.assert_called_once_with(
            self.catalog.catalog_id(), Coordinates("g1", "n1", "v1")
        )
        remove_dc.assert_called_once()
        set_cache_paths.assert_called_once()
        get_by_id_mock.assert_called_once_with(1)
        retrieve_and_load_resolve_result.assert_not_called()
        _clean_unfinished_installations_environment.assert_called_once()
        remove_solution.assert_called_once()
        self.assertIn(
            'Removing the unfinished installation of "g1:n1:v1"...',
            self.get_logs_as_string(),
        )
        self.assertTrue(self._lock_is_free(Coordinates("g1", "n1", "v1")))

    @patch(
        "album.core.controller.install_manager.dict_to_coordinates",
        return_value=Coordinates("g1", "n1", "v1"),
    )
    def test_clean_unfinished_installations_parent(self, _):
        parent_entry = CollectionIndex.CollectionSolution(
            {"group": "g0", "name": "n0", "version": "v0"}, {"catalog_id": 1}
        )

        # mocks
        remove_dc = MagicMock()
        self.album_controller.install_manager()._remove_disc_content_from_solution = (
            remove_dc
        )

        set_cache_paths = MagicMock()
        self.album_controller.collection_manager().solutions().set_cache_paths = (
            set_cache_paths
        )
        entry = CollectionIndex.CollectionSolution(
            {"group": "g1", "name": "n1", "version": "v1"},  # setup
            {
                "catalog_id": 1,
                "parent": parent_entry,
                "installation_unfinished": 1,
            },  # internal
        )
        get_unfinished_installation_solutions = MagicMock(return_value=[entry])
        self.album_controller.collection_manager().get_collection_index().get_unfinished_installation_solutions = (
            get_unfinished_installation_solutions
        )
        # looked up again holding the lock of the solution
        self.album_controller.collection_manager().get_collection_index().get_solution_by_catalog_grp_name_version = MagicMock(
            return_value=entry
        )

        get_by_id_mock = MagicMock(
            return_value=self.album_controller.collection_manager()
            .catalogs()
            .get_cache_catalog()
        )
        self.album_controller.collection_manager().catalogs().get_by_id = get_by_id_mock

        retrieve_and_load_resolve_result = MagicMock()
        self.album_controller.collection_manager().retrieve_and_load_resolve_result = (
            retrieve_and_load_resolve_result
        )

        _clean_unfinished_installations_environment = MagicMock()
        self.install_manager._clean_unfinished_installations_environment = (
            _clean_unfinished_installations_environment
        )

        remove_solution = MagicMock()
        self.album_controller.collection_manager().solutions().remove_solution = (
            remove_solution
        )

        # call
        self.install_manager.clean_unfinished_installations()

        # assert
        remove_dc.assert_called_once()
        set_cache_paths.assert_called_once()
        get_by_id_mock.assert_called_once_with(1)
        retrieve_and_load_resolve_result.assert_not_called()
        _clean_unfinished_installations_environment.assert_not_called()
        remove_solution.assert_called_once()

    def test_clean_unfinished_installations_empty(self):

        # mocks
        remove_dc = MagicMock()
        self.album_controller.install_manager()._remove_disc_content_from_solution = (
            remove_dc
        )

        set_cache_paths = MagicMock()
        self.album_controller.collection_manager().solutions().set_cache_paths = (
            set_cache_paths
        )
        get_by_id_mock = MagicMock(
            return_value=self.album_controller.collection_manager()
            .catalogs()
            .get_cache_catalog()
        )
        self.album_controller.collection_manager().catalogs().get_by_id = get_by_id_mock

        retrieve_and_load_resolve_result = MagicMock()
        self.album_controller.collection_manager().retrieve_and_load_resolve_result = (
            retrieve_and_load_resolve_result
        )

        _clean_unfinished_installations_environment = MagicMock()
        self.install_manager._clean_unfinished_installations_environment = (
            _clean_unfinished_installations_environment
        )

        set_uninstalled = MagicMock()
        self.album_controller.collection_manager().solutions().set_uninstalled = (
            set_uninstalled
        )

        # call
        self.install_manager.clean_unfinished_installations()

        # assert
        remove_dc.assert_not_called()
        set_cache_paths.assert_not_called()
        get_by_id_mock.assert_not_called()
        retrieve_and_load_resolve_result.assert_not_called()
        _clean_unfinished_installations_environment.assert_not_called()
        set_uninstalled.assert_not_called()

    def _mock_unfinished_installation(self, unfinished_now: int = 1) -> MagicMock:
        # g1:n1:v1 is marked unfinished, and still is when it is looked up again
        # holding its lock unless unfinished_now is 0
        collection_index = (
            self.album_controller.collection_manager().get_collection_index()
        )
        collection_index.get_unfinished_installation_solutions = MagicMock(
            return_value=[
                CollectionIndex.CollectionSolution(
                    {"group": "g1", "name": "n1", "version": "v1"},  # setup
                    {
                        "catalog_id": 1,
                        "parent": None,
                        "installation_unfinished": 1,
                    },  # internal
                )
            ]
        )
        collection_index.get_solution_by_catalog_grp_name_version = MagicMock(
            return_value=CollectionIndex.CollectionSolution(
                {"group": "g1", "name": "n1", "version": "v1"},  # setup
                {
                    "catalog_id": 1,
                    "parent": None,
                    "installation_unfinished": unfinished_now,
                },  # internal
            )
        )
        self.album_controller.collection_manager().catalogs().get_by_id = MagicMock(
            return_value=self.catalog
        )
        self.album_controller.collection_manager().solutions().set_cache_paths = (
            MagicMock()
        )
        self.install_manager._clean_unfinished_installations_environment = MagicMock()
        self.install_manager._remove_disc_content_from_solution = MagicMock()
        remove_solution = MagicMock()
        self.album_controller.collection_manager().solutions().remove_solution = (
            remove_solution
        )
        return remove_solution

    def test_clean_unfinished_installations_in_progress(self):
        remove_solution = self._mock_unfinished_installation()

        # another album process using the same base path installs it right now
        with self._lock_of_other_process(Coordinates("g1", "n1", "v1")):
            start = time.monotonic()
            # call
            self.install_manager.clean_unfinished_installations()

            # assert - not removed, without waiting for the other process
            self.assertLess(time.monotonic() - start, 1)
        remove_solution.assert_not_called()
        self.install_manager._remove_disc_content_from_solution.assert_not_called()
        self.install_manager._clean_unfinished_installations_environment.assert_not_called()
        self.assertNotIn("Removing the unfinished", self.get_logs_as_string())

    def test_clean_unfinished_installations_in_progress_in_this_thread(self):
        remove_solution = self._mock_unfinished_installation()

        # this thread installs it right now
        with self._solution_lock(Coordinates("g1", "n1", "v1")):
            # call
            self.install_manager.clean_unfinished_installations()

        # assert
        remove_solution.assert_not_called()
        self.install_manager._remove_disc_content_from_solution.assert_not_called()

    def test_clean_unfinished_installations_finished_meanwhile(self):
        # the installation finished before the lock was acquired
        remove_solution = self._mock_unfinished_installation(unfinished_now=0)

        # call
        self.install_manager.clean_unfinished_installations()

        # assert
        remove_solution.assert_not_called()
        self.install_manager._remove_disc_content_from_solution.assert_not_called()
        self.assertTrue(self._lock_is_free(Coordinates("g1", "n1", "v1")))

    def test__clean_unfinished_installations_environment_env_deleted(self):
        # mocks
        set_environment = MagicMock(return_value="myEnv")
        self.environment_manager.set_environment = set_environment

        remove_environment = MagicMock(return_value=True)
        self.environment_manager.remove_environment = remove_environment

        _remove_environment_link = MagicMock()
        self.install_manager._remove_environment_link = _remove_environment_link

        # prepare
        r = ResolveResult("mypath", None, None, None)
        # call
        self.install_manager._clean_unfinished_installations_environment(r)

        # assert
        set_environment.assert_called_once()
        remove_environment.assert_called_once_with("myEnv")

    def test__clean_unfinished_installations_environment_env_not_deleted(self):
        c = EmptyTestClass()
        c.name = lambda: "myName"

        # mocks
        set_environment = MagicMock(return_value="myEnv")
        self.environment_manager.set_environment = set_environment

        remove_environment = MagicMock(return_value=False)
        self.environment_manager.remove_environment = remove_environment

        # prepare
        r = ResolveResult("mypath", c, None, Coordinates("a", "b", "c"))
        # call
        self.install_manager._clean_unfinished_installations_environment(r)

        # assert
        set_environment.assert_called_once()
        remove_environment.assert_called_once_with("myEnv")


class TestInstallManagerCollectionParent(TestUnitCoreCommon):
    """Parent detection for solutions built from their collection entry.

    Such solutions carry no "dependencies", their parent is only known from the
    collection index.
    """

    def setUp(self):
        super().setUp()
        self.setup_collection()
        # the real environment manager needs micromamba
        self.album_controller._environment_manager = MagicMock()
        self.environment_manager = self.album_controller.environment_manager()
        self.install_manager: InstallManager = self.album_controller.install_manager()
        self.catalog = (
            self.album_controller.collection_manager().catalogs().get_cache_catalog()
        )
        self.parent_entry = CollectionIndex.CollectionSolution(
            {"group": "gp", "name": "np", "version": "vp", "doi": None},  # setup
            {"catalog_id": 1, "parent": None, "children": []},  # internal
        )

    def _mock_clean_unfinished_installations(
        self, unfinished_entry: CollectionIndex.CollectionSolution
    ) -> MagicMock:
        collection_manager = self.album_controller.collection_manager()
        collection_index = collection_manager.get_collection_index()
        collection_index.get_unfinished_installation_solutions = MagicMock(
            return_value=[unfinished_entry]
        )
        # looked up again holding the lock of the solution
        collection_index.get_solution_by_catalog_grp_name_version = MagicMock(
            return_value=unfinished_entry
        )
        collection_manager.catalogs().get_by_id = MagicMock(return_value=self.catalog)
        collection_manager.solutions().set_cache_paths = MagicMock()
        self.install_manager._remove_disc_content_from_solution = MagicMock()
        remove_solution = MagicMock()
        collection_manager.solutions().remove_solution = remove_solution
        return remove_solution

    def test_clean_unfinished_installations_child(self):
        child_entry = CollectionIndex.CollectionSolution(
            {"group": "g1", "name": "n1", "version": "v1"},  # setup
            {
                "catalog_id": 1,
                "parent": self.parent_entry,
                "installation_unfinished": 1,
            },  # internal
        )
        remove_solution = self._mock_clean_unfinished_installations(child_entry)

        # call
        self.install_manager.clean_unfinished_installations()

        # assert - the child runs in the environment of its parent, which stays
        self.environment_manager.set_environment.assert_not_called()
        self.environment_manager.remove_environment.assert_not_called()
        remove_solution.assert_called_once()

    def test_clean_unfinished_installations_no_parent(self):
        entry = CollectionIndex.CollectionSolution(
            {"group": "g1", "name": "n1", "version": "v1"},  # setup
            {"catalog_id": 1, "parent": None, "installation_unfinished": 1},  # internal
        )
        remove_solution = self._mock_clean_unfinished_installations(entry)
        self.environment_manager.set_environment.return_value = "myEnv"

        # call
        self.install_manager.clean_unfinished_installations()

        # assert
        self.environment_manager.set_environment.assert_called_once()
        self.environment_manager.remove_environment.assert_called_once_with("myEnv")
        remove_solution.assert_called_once()

    def test_uninstall_rm_dep_solution_not_loaded(self):
        child_entry = CollectionIndex.CollectionSolution(
            {"group": "g1", "name": "n1", "version": "v1", "doi": None},  # setup
            {"catalog_id": 1, "parent": self.parent_entry, "children": []},  # internal
        )
        resolve_result = ResolveResult(
            path=Path("aPath"),
            catalog=self.catalog,
            collection_entry=child_entry,
            coordinates=Coordinates("g1", "n1", "v1"),
        )

        # mocks
        collection_manager = self.album_controller.collection_manager()
        # the solution file cannot be loaded, the solution is built from its entry
        collection_manager.resolve_installed = MagicMock(return_value=resolve_result)
        collection_manager.load_resolve_result = MagicMock(side_effect=ValueError)
        get_by_id = MagicMock(return_value=self.catalog)
        collection_manager.catalogs().get_by_id = get_by_id
        self.install_manager._remove_disc_content_from_solution = MagicMock()
        remove_solution = MagicMock()
        collection_manager.solutions().remove_solution = remove_solution

        # the recursive call uninstalling the parent ends up in this mock
        uninstall_parent = MagicMock()
        self.install_manager._uninstall_parent = uninstall_parent

        # call
        self.install_manager.uninstall("g1:n1:v1", rm_dep=True)

        # assert
        remove_solution.assert_called_once()
        self.environment_manager.remove_environment.assert_not_called()
        get_by_id.assert_called_once_with(1)
        uninstall_parent.assert_called_once_with(
            "%s:gp:np:vp" % self.catalog.name(), True
        )

    def test_remove_dependencies_parent_declared_in_solution(self):
        # solution loaded from its file: the declared parent is used, as before
        solution = Solution(
            {
                "group": "g1",
                "name": "n1",
                "version": "v1",
                "dependencies": {"parent": {"resolve_solution": "gp:np:vp"}},
            }
        )
        get_by_id = MagicMock()
        self.album_controller.collection_manager().catalogs().get_by_id = get_by_id
        uninstall_parent = MagicMock()
        self.install_manager._uninstall_parent = uninstall_parent

        # call
        self.install_manager._remove_dependencies(solution, True, self.parent_entry)

        # assert
        uninstall_parent.assert_called_once_with("gp:np:vp", True)
        get_by_id.assert_not_called()

    def test_remove_dependencies_parent_from_its_catalog(self):
        # the parent the solution was installed into, as the collection records it
        solution = Solution(
            {
                "group": "g1",
                "name": "n1",
                "version": "v1",
                "dependencies": {
                    "parent": {"group": "gp", "name": "np", "version": "vp"}
                },
            }
        )
        parent_catalog = MagicMock()
        parent_catalog.name.return_value = "parent-catalog"
        get_by_id = MagicMock(return_value=parent_catalog)
        self.album_controller.collection_manager().catalogs().get_by_id = get_by_id
        uninstall_parent = MagicMock()
        self.install_manager._uninstall_parent = uninstall_parent

        # call
        self.install_manager._remove_dependencies(solution, True, self.parent_entry)

        # assert
        get_by_id.assert_called_once_with(1)
        uninstall_parent.assert_called_once_with("parent-catalog:gp:np:vp", True)

    def test_remove_dependencies_no_parent_declared_in_solution(self):
        # solution loaded from its file without parent: nothing to remove, as before
        solution = Solution(
            {
                "group": "g1",
                "name": "n1",
                "version": "v1",
                "dependencies": {"environment_file": "env.yml"},
            }
        )
        uninstall_parent = MagicMock()
        self.install_manager._uninstall_parent = uninstall_parent

        # call
        self.install_manager._remove_dependencies(solution, True, self.parent_entry)

        # assert
        uninstall_parent.assert_not_called()


def use_win_shell_per_thread(test):
    """Create Windows links (shortcuts) with a COM shell of the calling thread.

    Album creates them with one global Wscript.Shell, created by the first thread
    needing it. Using it from other threads fails with a com_error or crashes the
    process with an access violation. That happens without the install lock as well.
    """
    if sys.platform != "win32":
        return test

    # COM is initialized for the thread importing pythoncom first, keep that the
    # main thread, which creates links in other tests
    import pythoncom
    import win32com.client

    shells = threading.local()

    def get_win_shell():
        if not hasattr(shells, "shell"):
            pythoncom.CoInitialize()
            shells.shell = win32com.client.Dispatch("Wscript.Shell")
        return shells.shell

    return patch(
        "album.core.utils.operations.file_operations._get_global_win_shell",
        get_win_shell,
    )(test)


class TestInstallManagerParallel(TestUnitCoreCommon):
    """Album instances and processes installing into the same base path at the same time.

    Like two terminals calling "album install", see issue #186.
    """

    def setUp(self):
        super().setUp()
        self.setup_collection()
        # the second album instance, using the same base path
        self.other_controller = AlbumController(base_cache_path=Path(self.tmp_dir.name))
        with patch(
            "album.core.model.configuration.Configuration.get_initial_catalogs",
            return_value={},
        ):
            self.other_controller.collection_manager().load_or_create()
        # the real environment manager needs micromamba
        self.album_controller._environment_manager = MagicMock()
        self.other_controller._environment_manager = MagicMock()
        self.catalog = self.album_controller.catalogs().get_cache_catalog()

    def tearDown(self) -> None:
        self.other_controller.close()
        super().tearDown()

    def _write_solution(self, name: str, parent: str = None) -> str:
        dependencies = (
            ', dependencies={"parent": {"resolve_solution": "group:%s:0.1.0"}}' % parent
            if parent
            else ""
        )
        path = Path(self.tmp_dir.name).joinpath("%s.py" % name)
        path.write_text(
            "from album.runner.api import setup\n\n"
            'setup(group="group", name="%s", version="0.1.0", album_api_version="%s"%s)\n'
            % (name, TEST_ALBUM_API_VERSION, dependencies),
            encoding="utf-8",
        )
        return str(path)

    def _is_installed(self, name: str) -> bool:
        return self.album_controller.solutions().is_installed(
            self.catalog, Coordinates("group", name, "0.1.0")
        )

    def _unfinished_installations(self) -> list:
        return (
            self.album_controller.collection_manager()
            .get_collection_index()
            .get_unfinished_installation_solutions()
        )

    def _lock_of_other_process(self, name: str) -> FileLock:
        return lock_of_other_process(
            self.album_controller, self.catalog, Coordinates("group", name, "0.1.0")
        )

    def _wait_at_most(
        self, controller: AlbumController, name: str, seconds: float
    ) -> None:
        # waiting longer for the lock of the solution fails the test, instead of
        # after two hours
        controller.solutions().get_solution_lock(
            self.catalog, Coordinates("group", name, "0.1.0")
        )._timeout = seconds

    def test_install_installed_solution_does_not_wait(self):
        first = self._write_solution("first")
        install_manager = self.album_controller.install_manager()
        install_manager.install(first)
        self._wait_at_most(self.album_controller, "first", 0.2)

        # another album process holds the lock of the installed solution, e.g. to
        # install a child solution into its environment
        with self._lock_of_other_process("first"):
            # call - an installed solution, by path or by coordinates
            for solution_to_resolve in [first, "group:first:0.1.0"]:
                solution = install_manager.install(solution_to_resolve)

                # assert - returned right away
                self.assertEqual("first", solution.coordinates().name())

        self.assertIn(
            'Solution "first" already installed. Skipping...',
            self.get_logs_as_string(),
        )
        install_environment = (
            self.album_controller.environment_manager().install_environment
        )
        install_environment.assert_called_once()

    def test_install_does_not_wait_for_other_solution(self):
        second = self._write_solution("second")
        install_manager = self.album_controller.install_manager()
        self._wait_at_most(self.album_controller, "second", 0.2)

        # another album process installs another solution right now
        with self._lock_of_other_process("first"):
            # call
            install_manager.install(second)

        # assert - installed without waiting
        self.assertTrue(self._is_installed("second"))
        self.assertNotIn("Waiting", self.get_logs_as_string())

    def test_install_same_solution_waits(self):
        first = self._write_solution("first")
        install_manager = self.album_controller.install_manager()
        self._wait_at_most(self.album_controller, "first", 0.2)

        # another album process installs the same solution right now
        with self._lock_of_other_process("first"):
            # call
            with self.assertRaises(TimeoutError):
                install_manager.install(first)

        # assert
        self.assertFalse(self._is_installed("first"))
        install_environment = (
            self.album_controller.environment_manager().install_environment
        )
        install_environment.assert_not_called()

        # it can be installed once the other process has finished
        install_manager.install(first)
        self.assertTrue(self._is_installed("first"))

    def test_install_unfinished_solution_waits(self):
        first = self._write_solution("first")
        install_manager = self.album_controller.install_manager()
        install_manager.install(first)
        self._wait_at_most(self.album_controller, "first", 0.2)
        # another album process is installing it right now
        self.album_controller.solutions().set_installation_unfinished(
            self.catalog, Coordinates("group", "first", "0.1.0")
        )

        with self._lock_of_other_process("first"):
            # call
            with self.assertRaises(TimeoutError):
                install_manager.install(first)

        # assert - not taken for installed, not removed as unfinished
        self.assertFalse(self._is_installed("first"))
        self.assertEqual(1, len(self._unfinished_installations()))

    def test_install_removes_installation_left_unfinished(self):
        first = self._write_solution("first")
        second = self._write_solution("second")
        install_manager = self.album_controller.install_manager()
        install_manager.install(first)
        # an album process ended (e.g. was killed) while installing it, its lock is free
        self.album_controller.solutions().set_installation_unfinished(
            self.catalog, Coordinates("group", "first", "0.1.0")
        )

        # call
        install_manager.install(second)

        # assert
        self.assertTrue(self._is_installed("second"))
        self.assertEqual([], self._unfinished_installations())
        self.assertIsNone(
            self.album_controller.collection_manager()
            .get_collection_index()
            .get_solution_by_catalog_grp_name_version(
                self.catalog.catalog_id(), Coordinates("group", "first", "0.1.0")
            )
        )
        environment_manager = self.album_controller.environment_manager()
        environment_manager.remove_environment.assert_called_once()
        self.assertIn(
            'Removing the unfinished installation of "group:first:0.1.0"...',
            self.get_logs_as_string(),
        )

    def test_install_failed_removed_right_away(self):
        first = self._write_solution("first")
        install_manager = self.album_controller.install_manager()
        environment_manager = self.album_controller.environment_manager()
        environment_manager.install_environment.side_effect = RuntimeError(
            "Cannot create environment!"
        )

        # call
        with self.assertRaises(RuntimeError):
            install_manager.install(first)

        # assert - nothing is left for the next installation (e.g. by another album
        # process) to remove
        self.assertEqual([], self._unfinished_installations())
        self.assertIsNone(
            self.album_controller.collection_manager()
            .get_collection_index()
            .get_solution_by_catalog_grp_name_version(
                self.catalog.catalog_id(), Coordinates("group", "first", "0.1.0")
            )
        )
        environment_manager.remove_environment.assert_called_once()
        self.assertTrue(
            lock_is_free(
                self.album_controller,
                self.catalog,
                Coordinates("group", "first", "0.1.0"),
            )
        )

        # it can be installed again
        environment_manager.install_environment.side_effect = None
        install_manager.install(first)
        self.assertTrue(self._is_installed("first"))

    @use_win_shell_per_thread
    def test_install_in_parallel(self):
        first = self._write_solution("first")
        second = self._write_solution("second")
        first_installing = threading.Event()
        second_installed = threading.Event()
        errors = []

        def create_first_environment(*args):
            # the first installation is in progress (marked "unfinished") while the
            # second album instance installs another solution, not waiting for it
            first_installing.set()
            if not second_installed.wait(30):
                errors.append("the second installation waited for the first one")

        self.album_controller.environment_manager().install_environment.side_effect = (
            create_first_environment
        )

        # the second album instance must not remove the first installation
        other_install_manager = self.other_controller.install_manager()
        remove_disc_content = MagicMock()
        other_install_manager._remove_disc_content_from_solution = remove_disc_content

        def install(controller, path, installed=None):
            try:
                controller.install_manager().install(path)
                if installed:
                    installed.set()
            except Exception as e:
                errors.append(e)

        # waiting for a lock that is not released fails the test, not after two hours
        self._wait_at_most(self.album_controller, "first", 30)
        self._wait_at_most(self.other_controller, "second", 30)
        first_thread = threading.Thread(
            target=install, args=(self.album_controller, first), daemon=True
        )
        second_thread = threading.Thread(
            target=install,
            args=(self.other_controller, second, second_installed),
            daemon=True,
        )

        # call
        first_thread.start()
        self.assertTrue(first_installing.wait(30))
        second_thread.start()
        second_thread.join(60)
        first_thread.join(60)

        # assert
        self.assertFalse(first_thread.is_alive())
        self.assertFalse(second_thread.is_alive())
        self.assertEqual([], errors)
        self.assertTrue(self._is_installed("first"))
        self.assertTrue(self._is_installed("second"))
        self.assertEqual([], self._unfinished_installations())
        remove_disc_content.assert_not_called()
        other_environment_manager = self.other_controller.environment_manager()
        other_environment_manager.remove_environment.assert_not_called()
        other_environment_manager.install_environment.assert_called_once()

    @use_win_shell_per_thread
    def test_install_children_of_the_same_parent(self):
        parent = self._write_solution("parent")
        first_child = self._write_solution("child1", parent="parent")
        second_child = self._write_solution("child2", parent="parent")
        self.album_controller.install_manager().install(parent)
        first_child_installing = threading.Event()
        first_child_may_finish = threading.Event()
        second_child_installing = threading.Event()
        errors = []

        def install_first_child_routine(*args):
            # the first child is installed into the environment of the parent
            first_child_installing.set()
            first_child_may_finish.wait(30)

        self.album_controller.install_manager()._run_solution_install_routine = (
            MagicMock(side_effect=install_first_child_routine)
        )
        self.other_controller.install_manager()._run_solution_install_routine = (
            MagicMock(side_effect=lambda *args: second_child_installing.set())
        )

        def install(controller, path):
            try:
                controller.install_manager().install(path)
            except Exception as e:
                errors.append(e)

        # waiting for a lock that is not released fails the test, not after two hours
        for controller in [self.album_controller, self.other_controller]:
            self._wait_at_most(controller, "parent", 30)
        first_thread = threading.Thread(
            target=install, args=(self.album_controller, first_child), daemon=True
        )
        second_thread = threading.Thread(
            target=install, args=(self.other_controller, second_child), daemon=True
        )

        # call
        first_thread.start()
        self.assertTrue(first_child_installing.wait(30))
        second_thread.start()

        # assert - the second child waits for the parent until the first is installed
        self.assertFalse(second_child_installing.wait(1))
        first_child_may_finish.set()
        first_thread.join(60)
        second_thread.join(60)
        self.assertTrue(second_child_installing.is_set())
        self.assertFalse(first_thread.is_alive())
        self.assertFalse(second_thread.is_alive())
        self.assertEqual([], errors)
        for name in ["parent", "child1", "child2"]:
            self.assertTrue(self._is_installed(name), name)
        self.assertEqual([], self._unfinished_installations())


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path

from album.core.model.catalog import Catalog
from album.core.model.resolve_result import ResolveResult
from album.runner.core.model.coordinates import Coordinates
from album.runner.core.model.solution import Solution
from test.unit.test_unit_core_common import TestUnitCoreCommon
from unittest.mock import patch, MagicMock


class TestEnvironmentManager(TestUnitCoreCommon):
    def setUp(self):
        super().setUp()
        self.environment_manager = self.album_controller.environment_manager()
        self.active_solution = self.setup_helper_solutions()
        self.catalog = Catalog("testid", "testname", "test_path")


    def tearDown(self) -> None:
        super().tearDown()

    def setup_helper_solutions(self):
        active_solution = Solution(self.get_solution_dict_with_dependecies())
        active_solution.setup()["dependencies"]["environment_file"] = "http://test.de"
        active_solution._installation._package_path = Path(self.tmp_dir.name)
        active_solution._coordinates = Coordinates("testid", "test", "1.0.0")

        return active_solution

    @patch("album.core.controller.conda_lock_manager.CondaLockManager.install")
    @patch("album.core.model.environment.Environment._prepare_env_file")
    def test_install_environment_from_lockfile(self, mock_prepare_env_file, mock_install):
        # prepare
        self.active_solution._installation._package_path.joinpath('solution.conda-lock.yml').touch()
        resolve = ResolveResult(None, self.catalog, MagicMock(), self.active_solution.coordinates(),
                                loaded_solution=self.active_solution)
        internal_cache_path = MagicMock(return_value=Path(self.tmp_dir.name))
        resolve.loaded_solution().installation().internal_cache_path = internal_cache_path

        # call
        self.environment_manager.install_environment(resolve)

        # assert
        mock_install.assert_called_once()

    # FIXME: check if this is working with mamba, since its only testing the package manager install function and not the env_installer_manager
    @patch("album.core.controller.package_manager.PackageManager.install")
    @patch("album.core.model.environment.Environment._prepare_env_file")
    def test_install_environment_from_yml(self, _prepare_env, create_function):
        # prepare
        resolve = ResolveResult(None, self.catalog, MagicMock(), self.active_solution.coordinates(),
                                loaded_solution=self.active_solution)
        internal_cache_path = MagicMock(return_value=Path(self.tmp_dir.name))
        resolve.loaded_solution().installation().internal_cache_path = internal_cache_path

        # call
        self.environment_manager.install_environment(resolve)

        # assert
        create_function.assert_called_once()

    @unittest.skip("Needs to be implemented!")
    def test_set_environment(self):
        # ToDo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test_remove_environment(self):
        # ToDo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_environment_base_folder(self):
        # ToDo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test_run_scripts(self):
        # ToDo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_environment_name(self):
        # ToDo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test_remove_disc_content_from_environment(self):
        # ToDo: implement!
        pass

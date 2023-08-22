import io
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from pathlib import Path
from unittest.mock import patch
from unittest.mock import patch, MagicMock

import yaml
from album.core.controller.environment_manager import EnvironmentManager
from album.core.model.catalog import Catalog
from album.core.model.resolve_result import ResolveResult
from album.environments.utils.file_operations import get_dict_from_yml
from album.runner.core.model.coordinates import Coordinates
from album.runner.core.model.solution import Solution
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestEnvironmentManager(TestUnitCoreCommon):
    test_environment_name = "unittest"

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

    @patch(
        "album.environments.controller.conda_lock_manager.CondaLockManager.create_environment_from_lockfile"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager._prepare_env_file"
    )
    def test_install_environment_from_lockfile(
        self, mock_prepare_env_file, mock_create_environment_from_lockfile
    ):
        # prepare
        self.active_solution._installation._package_path.joinpath(
            "solution.conda-lock.yml"
        ).touch()
        resolve = ResolveResult(
            None,
            self.catalog,
            MagicMock(),
            self.active_solution.coordinates(),
            loaded_solution=self.active_solution,
        )
        internal_cache_path = MagicMock(return_value=Path(self.tmp_dir.name))
        resolve.loaded_solution().installation().internal_cache_path = (
            internal_cache_path
        )

        # call
        self.environment_manager.install_environment(resolve)

        # assert
        mock_create_environment_from_lockfile.assert_called_once()

    # FIXME: check if this is working with mamba, since its only testing the package manager install function and not the env_installer_manager
    @patch("album.environments.controller.package_manager.PackageManager.install")
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager._prepare_env_file"
    )
    def test_install_environment_from_yml(self, _prepare_env, create_function):
        # prepare
        resolve = ResolveResult(
            None,
            self.catalog,
            MagicMock(),
            self.active_solution.coordinates(),
            loaded_solution=self.active_solution,
        )
        internal_cache_path = MagicMock(return_value=Path(self.tmp_dir.name))
        resolve.loaded_solution().installation().internal_cache_path = (
            internal_cache_path
        )

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

    def test__prepare_env_file_no_deps(self):
        EnvironmentManager._prepare_env_file(None, Path(self.tmp_dir.name), None, None)

    def test__prepare_env_file_empty_deps(self):
        EnvironmentManager._prepare_env_file({}, Path(self.tmp_dir.name), None, None)

    @patch(
        "album.core.controller.environment_manager.create_path_recursively",
        return_value="createdPath",
    )
    def test__prepare_env_file_invalid_file(self, create_path_mock):
        with self.assertRaises(TypeError) as context:
            EnvironmentManager._prepare_env_file(
                {"environment_file": "env_file"},
                Path(self.closed_tmp_file.name),
                None,
                None,
            )
            self.assertIn("Yaml file must either be a url", str(context.exception))

        create_path_mock.assert_called_once()

    @patch("album.core.controller.environment_manager.copy")
    @patch(
        "album.core.controller.environment_manager.create_path_recursively",
        return_value="createdPath",
    )
    def test__prepare_env_file_valid_file(self, create_path_mock, copy_mock):
        # mocks
        copy_mock.return_value = self.closed_tmp_file.name
        with open(self.closed_tmp_file.name, mode="w") as tmp_file:
            tmp_file.write("""name: test""")

        r = EnvironmentManager._prepare_env_file(
            {"environment_file": self.closed_tmp_file.name},
            Path(self.closed_tmp_file.name),
            None,
            None,
        )

        self.assertEqual(self.closed_tmp_file.name, r)

        create_path_mock.assert_called_once()
        copy_mock.assert_called_once()

    @patch("album.core.controller.environment_manager.download_resource")
    @patch(
        "album.core.controller.environment_manager.create_path_recursively",
        return_value="createdPath",
    )
    def test__prepare_env_file_valid_url(self, create_path_mock, download_mock):
        # mocks
        download_mock.return_value = self.closed_tmp_file.name
        with open(self.closed_tmp_file.name, mode="w") as tmp_file:
            tmp_file.write("""name: test""")

        url = "http://test.de"

        r = EnvironmentManager._prepare_env_file(
            {"environment_file": url}, Path("aPath"), self.test_environment_name, None
        )

        self.assertEqual(self.closed_tmp_file.name, r)

        create_path_mock.assert_called_once()
        download_mock.assert_called_once_with(
            url, Path("aPath").joinpath("%s.yml" % self.test_environment_name)
        )

    @patch(
        "album.core.controller.environment_manager.create_path_recursively",
        return_value="createdPath",
    )
    def test__prepare_env_file_invalid_StringIO(self, create_path_mock):
        _cache_path = Path(tempfile.gettempdir())

        string_io = io.StringIO("""testStringIo""")

        with self.assertRaises(TypeError):
            EnvironmentManager._prepare_env_file(
                {"environment_file": string_io},
                _cache_path,
                self.test_environment_name,
                None,
            )

        self.assertTrue(
            Path(tempfile.gettempdir())
            .joinpath("%s.yml" % self.test_environment_name)
            .exists()
        )

        create_path_mock.assert_called_once()

    @patch(
        "album.core.controller.environment_manager.create_path_recursively",
        return_value="createdPath",
    )
    def test__prepare_env_file_valid_StringIO(self, create_path_mock):
        _cache_path = Path(tempfile.gettempdir())

        string_io = io.StringIO("""name: value""")

        r = EnvironmentManager._prepare_env_file(
            {"environment_file": string_io},
            _cache_path,
            self.test_environment_name,
            "0.1.0",
        )

        self.assertEqual(
            Path(tempfile.gettempdir()).joinpath("%s.yml" % self.test_environment_name),
            r,
        )

        # overwritten name
        res = get_dict_from_yml(
            Path(tempfile.gettempdir()).joinpath("%s.yml" % self.test_environment_name)
        )
        self.assertEqual(res["name"], self.test_environment_name)

        create_path_mock.assert_called_once()

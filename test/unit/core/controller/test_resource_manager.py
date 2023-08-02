import copy
import shutil
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock

import yaml

from album.core.controller.resource_manager import ResourceManager
from album.core.model.catalog import Catalog
from album.core.model.default_values import DefaultValues
from album.runner.core.model.solution import Solution
from test.unit.test_unit_core_common import (
    TestCatalogAndCollectionCommon,
)


class TestResourceManager(TestCatalogAndCollectionCommon):

    def setUp(self):
        super().setUp()
        self.setup_solution_no_env()
        self.resource_manager = self.album_controller.resource_manager()

    def tearDown(self):
        super().tearDown()

    def write_test_env_file(self):
        env_file = Path(self.tmp_dir.name).joinpath('environment.yml')
        env_content = """name: Dummy-Solution18
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.8
  - pip
"""
        with open(env_file, "w") as f:
            f.write(env_content)
        return env_file

    @patch("album.core.controller.resource_manager.get_deploy_dict")
    def test__create_yaml_file_in_local_src(self, deploy_dict_mock):
        deploy_dict_mock.return_value = {
            "name": "tsn",
            "group": "tsg",
            "version": "tsv",
        }

        target = Path(self.tmp_dir.name)

        y_path = ResourceManager._create_yaml_file_in_local_src(
            self.active_solution, target
        )

        self.assertEqual(target.joinpath("solution.yml"), y_path)

        f = open(y_path)
        f_content = f.readlines()
        f.close()

        self.assertEqual(["group: tsg\n", "name: tsn\n", "version: tsv\n"], f_content)

    @patch("album.core.controller.resource_manager.create_changelog_file", return_value="changelogfile")
    @patch("album.environments.controller.conda_lock_manager.CondaLockManager.create_conda_lock_file", return_value="lockfile")
    def test_build_solution_files(self, create_changelog_file, create_conda_lock_file):
        # prepare
        catalog_src_path, _ = self.setup_empty_catalog("test_cat")
        catalog = Catalog(
            0,
            "test_cat",
            src=catalog_src_path,
            path=Path(self.tmp_dir.name).joinpath("catalog_cache_path"),
        )

        # mock
        _create_yaml_file_in_local_src = MagicMock(return_value="ymlfile")
        self.resource_manager._create_yaml_file_in_local_src = (
            _create_yaml_file_in_local_src
        )
        write_solution_environment_file = MagicMock(return_value=Path(self.tmp_dir.name).joinpath("env.yml"))
        self.resource_manager.write_solution_environment_file = write_solution_environment_file

        # call
        r = self.resource_manager.write_solution_files(
            catalog, catalog_src_path, self.active_solution, Path("deployPath")
        )

        expected = ["ymlfile", "changelogfile", "lockfile"]
        # assert
        self.assertListEqual(expected, r)

    @patch("album.core.controller.resource_manager.download_resource")
    @patch("album.core.model.environment.create_path_recursively", return_value="createdPath")
    def test_write_solution_env_file(self, create_path_mock, download_mock):
        # prepare
        solution_no_env = Solution(self.get_solution_dict_with_dependecies())
        solution_no_env.setup()["dependencies"]["environment_file"] = ""
        framework = "conda-forge::%s=%s" % (
            DefaultValues.runner_api_packet_name.value,
            DefaultValues.runner_api_packet_version.value,
        )
        expected_content_no_env = """['channels:\\n', '- defaults\\n', 'dependencies:\\n', '- python=3.9\\n', '- conda-forge::%s=%s\\n', '- conda-forge::setuptools>=59.7.0\\n']"""\
                            % (DefaultValues.runner_api_packet_name.value, DefaultValues.runner_api_packet_version.value)
        expected_content = """['channels:\\n', '- conda-forge\\n', '- defaults\\n', 'dependencies:\\n', '- python=3.8\\n', '- pip\\n', '- conda-forge::%s=%s\\n', '- conda-forge::setuptools>=59.7.0\\n', 'name: Dummy-Solution18\\n']"""\
                            % (DefaultValues.runner_api_packet_name.value, DefaultValues.runner_api_packet_version.value)

        expected_content_with_setuptools = """['channels:\\n', '- conda-forge\\n', '- defaults\\n', 'dependencies:\\n', '- python=3.8\\n', '- pip\\n', '- conda-forge::setuptools\\n', '- conda-forge::%s=%s\\n', '- conda-forge::setuptools>=59.7.0\\n', 'name: Dummy-Solution18\\n']"""\
                            % (DefaultValues.runner_api_packet_name.value, DefaultValues.runner_api_packet_version.value)

        solution_env_string = Solution(self.get_solution_dict_with_dependecies())
        solution_env_string.setup()["dependencies"]["environment_file"] = """name: Dummy-Solution18
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.8
  - pip
"""

        solution_env_string_setuptools = Solution(self.get_solution_dict_with_dependecies())
        solution_env_string_setuptools.setup()["dependencies"]["environment_file"] = """name: Dummy-Solution18
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.8
  - pip
  - conda-forge::setuptools
"""

        solution_env_url = Solution(self.get_solution_dict_with_dependecies())
        solution_env_url.setup()["dependencies"]["environment_file"] = "http://test.de"

        solution_string_io = Solution(self.get_solution_dict_with_dependecies())
        solution_string_io.setup()["dependencies"]["environment_file"] = StringIO("""name: Dummy-Solution18
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.8
  - pip
""")

        solution_faulty_dict = Solution(self.get_solution_dict_with_dependecies())
        solution_faulty_dict.setup()["dependencies"]["environment_file"] = {"name": "Dummy-Solution18"}

        solution_faulty_env_file = Solution(self.get_solution_dict_with_dependecies())
        solution_faulty_env_file.setup()["dependencies"]["environment_file"] = 1

        solution_faulty_string = Solution(self.get_solution_dict_with_dependecies())
        solution_faulty_string.setup()["dependencies"]["environment_file"] = "3"

        # calls and asserts
        self.resource_manager.write_solution_environment_file(solution_no_env, Path(self.tmp_dir.name))
        self.assertTrue(Path(self.tmp_dir.name).joinpath("environment.yml").is_file())
        with open(Path(self.tmp_dir.name).joinpath("environment.yml")) as f:
            self.assertEqual(expected_content_no_env, repr(f.readlines()))

        self.resource_manager.write_solution_environment_file(solution_env_string, Path(self.tmp_dir.name))
        self.assertTrue(Path(self.tmp_dir.name).joinpath("environment.yml").is_file())
        with open(Path(self.tmp_dir.name).joinpath("environment.yml")) as f:
            self.assertEqual(expected_content, repr(f.readlines()))
        Path(self.tmp_dir.name).joinpath("environment.yml").unlink()

        self.resource_manager.write_solution_environment_file(solution_env_string_setuptools, Path(self.tmp_dir.name))
        self.assertTrue(Path(self.tmp_dir.name).joinpath("environment.yml").is_file())
        with open(Path(self.tmp_dir.name).joinpath("environment.yml")) as f:
            self.assertEqual(expected_content_with_setuptools, repr(f.readlines()))
        Path(self.tmp_dir.name).joinpath("environment.yml").unlink()

        self.write_test_env_file()  # create test environment file since the download is mocked
        self.resource_manager.write_solution_environment_file(solution_env_url, Path(self.tmp_dir.name))
        self.assertTrue(Path(self.tmp_dir.name).joinpath("environment.yml").is_file())
        with open(Path(self.tmp_dir.name).joinpath("environment.yml")) as f:
            self.assertEqual(expected_content, repr(f.readlines()))
        Path(self.tmp_dir.name).joinpath("environment.yml").unlink()

        self.resource_manager.write_solution_environment_file(solution_string_io, Path(self.tmp_dir.name))
        self.assertTrue(Path(self.tmp_dir.name).joinpath("environment.yml").is_file())
        with open(Path(self.tmp_dir.name).joinpath("environment.yml")) as f:
            self.assertEqual(expected_content, repr(f.readlines()))

        with self.assertRaises(RuntimeError):
            self.resource_manager.write_solution_environment_file(solution_faulty_dict, Path(self.tmp_dir.name))

        with self.assertRaises(RuntimeError):
            self.resource_manager.write_solution_environment_file(solution_faulty_env_file, Path(self.tmp_dir.name))

        with self.assertRaises(TypeError):
            self.resource_manager.write_solution_environment_file(solution_faulty_string, Path(self.tmp_dir.name))


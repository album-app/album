from io import StringIO
from pathlib import Path
from test.unit.test_unit_core_common import TestCatalogAndCollectionCommon
from unittest.mock import MagicMock, patch

from album.core.controller.resource_manager import ResourceManager
from album.core.model.catalog import Catalog
from album.core.model.default_values import DefaultValues
from album.runner.core.model.solution import Solution


class TestResourceManager(TestCatalogAndCollectionCommon):
    def setUp(self):
        super().setUp()
        self.setup_solution_no_env()
        self.resource_manager = self.album_controller.resource_manager()

    def tearDown(self):
        super().tearDown()

    def write_test_env_file(self):
        env_file = Path(self.tmp_dir.name).joinpath("environment.yml")
        env_content = """name: Dummy-Solution18
channels:
  - conda-forge
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

    @patch(
        "album.core.controller.resource_manager.create_changelog_file",
        return_value="changelogfile",
    )
    @patch(
        "album.environments.controller.conda_lock_manager.CondaLockManager.create_conda_lock_file",
        return_value="lockfile",
    )
    def test_build_solution_files(
        self, create_conda_lock_file_mock, create_changelog_file_mock
    ):
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
        write_solution_environment_file = MagicMock(
            return_value=Path(self.tmp_dir.name).joinpath("env.yml")
        )
        self.resource_manager.write_solution_environment_file = (
            write_solution_environment_file
        )

        # call — no_conda_lock=False so the lock file path is included
        r = self.resource_manager.write_solution_files(
            catalog, catalog_src_path, self.active_solution, Path("deployPath"), False
        )

        expected = ["ymlfile", "changelogfile", "lockfile"]
        # assert
        self.assertListEqual(expected, r)

    @patch(
        "album.core.controller.resource_manager.create_changelog_file",
        return_value="changelogfile",
    )
    @patch(
        "album.environments.controller.conda_lock_manager.CondaLockManager.create_conda_lock_file",
        return_value="lockfile",
    )
    def test_build_solution_files_preserves_user_changelog(
        self, create_conda_lock_file_mock, create_changelog_file_mock
    ):
        """When the deploy path is a directory containing a CHANGELOG.md, the
        user-provided file must be kept — create_changelog_file must NOT be
        called and the auto-generated version must NOT overwrite it."""
        # prepare
        catalog_src_path, _ = self.setup_empty_catalog("test_cat")
        catalog = Catalog(
            0,
            "test_cat",
            src=catalog_src_path,
            path=Path(self.tmp_dir.name).joinpath("catalog_cache_path"),
        )

        # create a deploy directory with a user-provided CHANGELOG.md
        deploy_dir = Path(self.tmp_dir.name).joinpath("deploy_dir")
        deploy_dir.mkdir()
        solution_file = deploy_dir.joinpath("solution.py")
        solution_file.write_text(
            "from album.runner.api import setup\nsetup(name='tsn', group='tsg', version='tsv')\n"
        )
        user_changelog = deploy_dir.joinpath("CHANGELOG.md")
        user_changelog.write_text(
            "# My handwritten changelog\n## [tsv] - 2026-01-01\n- My change\n"
        )

        # mock
        _create_yaml_file_in_local_src = MagicMock(return_value="ymlfile")
        self.resource_manager._create_yaml_file_in_local_src = (
            _create_yaml_file_in_local_src
        )
        write_solution_environment_file = MagicMock(
            return_value=Path(self.tmp_dir.name).joinpath("env.yml")
        )
        self.resource_manager.write_solution_environment_file = (
            write_solution_environment_file
        )

        # call
        r = self.resource_manager.write_solution_files(
            catalog, catalog_src_path, self.active_solution, deploy_dir, False
        )

        # assert — create_changelog_file must NOT have been called
        create_changelog_file_mock.assert_not_called()

        # the user's CHANGELOG.md path should be in the result (from the copy)
        changelog_paths = [str(p) for p in r if "CHANGELOG" in str(p)]
        self.assertEqual(1, len(changelog_paths))

        # verify the user's content is preserved, not overwritten

        suffix = (
            self.album_controller.configuration().get_solution_path_suffix_unversioned(
                self.active_solution.coordinates()
            )
        )
        committed_changelog = Path(catalog_src_path).joinpath(suffix, "CHANGELOG.md")
        self.assertIn("My handwritten changelog", committed_changelog.read_text())

    @patch("album.core.controller.resource_manager.download_resource")
    @patch(
        "album.core.model.environment.create_path_recursively",
        return_value="createdPath",
    )
    def test_write_solution_env_file(self, create_path_mock, download_mock):
        # prepare
        solution_no_env = Solution(self.get_solution_dict_with_dependecies())
        solution_no_env.setup()["dependencies"]["environment_file"] = ""
        framework = "conda-forge::{}={}".format(
            DefaultValues.runner_api_packet_name.value,
            DefaultValues.runner_api_packet_version.value,
        )
        expected_content_no_env = (
            """['channels:\\n', 'dependencies:\\n', '- python=3.9\\n', '- conda-forge::%s=%s\\n', '- conda-forge::setuptools>=59.7.0\\n']"""
            % (
                DefaultValues.runner_api_packet_name.value,
                DefaultValues.runner_api_packet_version.value,
            )
        )
        expected_content = (
            """['channels:\\n', '- conda-forge\\n', 'dependencies:\\n', '- python=3.8\\n', '- pip\\n', '- conda-forge::%s=%s\\n', '- conda-forge::setuptools>=59.7.0\\n', 'name: Dummy-Solution18\\n']"""
            % (
                DefaultValues.runner_api_packet_name.value,
                DefaultValues.runner_api_packet_version.value,
            )
        )

        expected_content_with_setuptools = (
            """['channels:\\n', '- conda-forge\\n', 'dependencies:\\n', '- python=3.8\\n', '- pip\\n', '- conda-forge::setuptools\\n', '- conda-forge::%s=%s\\n', '- conda-forge::setuptools>=59.7.0\\n', 'name: Dummy-Solution18\\n']"""
            % (
                DefaultValues.runner_api_packet_name.value,
                DefaultValues.runner_api_packet_version.value,
            )
        )

        solution_env_string = Solution(self.get_solution_dict_with_dependecies())
        solution_env_string.setup()["dependencies"][
            "environment_file"
        ] = """name: Dummy-Solution18
channels:
  - conda-forge
dependencies:
  - python=3.8
  - pip
"""

        solution_env_string_setuptools = Solution(
            self.get_solution_dict_with_dependecies()
        )
        solution_env_string_setuptools.setup()["dependencies"][
            "environment_file"
        ] = """name: Dummy-Solution18
channels:
  - conda-forge
dependencies:
  - python=3.8
  - pip
  - conda-forge::setuptools
"""

        solution_env_url = Solution(self.get_solution_dict_with_dependecies())
        solution_env_url.setup()["dependencies"]["environment_file"] = "http://test.de"

        solution_string_io = Solution(self.get_solution_dict_with_dependecies())
        solution_string_io.setup()["dependencies"]["environment_file"] = StringIO(
            """name: Dummy-Solution18
channels:
  - conda-forge
dependencies:
  - python=3.8
  - pip
"""
        )

        solution_faulty_dict = Solution(self.get_solution_dict_with_dependecies())
        solution_faulty_dict.setup()["dependencies"]["environment_file"] = {
            "name": "Dummy-Solution18"
        }

        solution_faulty_env_file = Solution(self.get_solution_dict_with_dependecies())
        solution_faulty_env_file.setup()["dependencies"]["environment_file"] = 1

        solution_faulty_string = Solution(self.get_solution_dict_with_dependecies())
        solution_faulty_string.setup()["dependencies"]["environment_file"] = "3"

        # calls and asserts
        self.resource_manager.write_solution_environment_file(
            solution_no_env, Path(self.tmp_dir.name)
        )
        self.assertTrue(Path(self.tmp_dir.name).joinpath("environment.yml").is_file())
        with open(Path(self.tmp_dir.name).joinpath("environment.yml")) as f:
            self.assertEqual(expected_content_no_env, repr(f.readlines()))

        self.resource_manager.write_solution_environment_file(
            solution_env_string, Path(self.tmp_dir.name)
        )
        self.assertTrue(Path(self.tmp_dir.name).joinpath("environment.yml").is_file())
        with open(Path(self.tmp_dir.name).joinpath("environment.yml")) as f:
            self.assertEqual(expected_content, repr(f.readlines()))
        Path(self.tmp_dir.name).joinpath("environment.yml").unlink()

        self.resource_manager.write_solution_environment_file(
            solution_env_string_setuptools, Path(self.tmp_dir.name)
        )
        self.assertTrue(Path(self.tmp_dir.name).joinpath("environment.yml").is_file())
        with open(Path(self.tmp_dir.name).joinpath("environment.yml")) as f:
            self.assertEqual(expected_content_with_setuptools, repr(f.readlines()))
        Path(self.tmp_dir.name).joinpath("environment.yml").unlink()

        self.write_test_env_file()  # create test environment file since the download is mocked
        self.resource_manager.write_solution_environment_file(
            solution_env_url, Path(self.tmp_dir.name)
        )
        self.assertTrue(Path(self.tmp_dir.name).joinpath("environment.yml").is_file())
        with open(Path(self.tmp_dir.name).joinpath("environment.yml")) as f:
            self.assertEqual(expected_content, repr(f.readlines()))
        Path(self.tmp_dir.name).joinpath("environment.yml").unlink()

        self.resource_manager.write_solution_environment_file(
            solution_string_io, Path(self.tmp_dir.name)
        )
        self.assertTrue(Path(self.tmp_dir.name).joinpath("environment.yml").is_file())
        with open(Path(self.tmp_dir.name).joinpath("environment.yml")) as f:
            self.assertEqual(expected_content, repr(f.readlines()))

        with self.assertRaises(RuntimeError):
            self.resource_manager.write_solution_environment_file(
                solution_faulty_dict, Path(self.tmp_dir.name)
            )

        with self.assertRaises(RuntimeError):
            self.resource_manager.write_solution_environment_file(
                solution_faulty_env_file, Path(self.tmp_dir.name)
            )

        with self.assertRaises(TypeError):
            self.resource_manager.write_solution_environment_file(
                solution_faulty_string, Path(self.tmp_dir.name)
            )

    def test_handle_env_file_dependency(self):
        _handle_env_file_string = MagicMock()
        self.resource_manager._handle_env_file_string = _handle_env_file_string
        _handle_env_file_stream = MagicMock()
        self.resource_manager._handle_env_file_stream = _handle_env_file_stream
        _handle_env_file_dict = MagicMock()
        self.resource_manager._handle_env_file_dict = _handle_env_file_dict

        # case 1: string
        self.resource_manager.handle_env_file_dependency(
            "test", Path(self.tmp_dir.name)
        )
        _handle_env_file_string.assert_called_once()

        # case 2: StringIO
        self.resource_manager.handle_env_file_dependency(
            StringIO("test"), Path(self.tmp_dir.name)
        )
        _handle_env_file_stream.assert_called_once()

        # case 3: dict
        self.resource_manager.handle_env_file_dependency(
            {"test": "test"}, Path(self.tmp_dir.name)
        )
        _handle_env_file_dict.assert_called_once()

        # case 4: error
        with self.assertRaises(TypeError):
            self.resource_manager.handle_env_file_dependency(1, Path(self.tmp_dir.name))

    @patch("album.core.controller.resource_manager.download_resource")
    def test__handle_env_file_string_valid_url(self, download_mock):
        test_yml_to_be_downloaded = Path(self.tmp_dir.name).joinpath("test_dl.yml")
        # touch file
        test_yml_to_be_downloaded.touch()

        # create tmp yml file named test.yml
        test_yml = Path(self.tmp_dir.name).joinpath("test.yml")
        with open(test_yml, mode="w") as tmp_file:
            tmp_file.write("""name: test""")

        url = "http://test.de"

        # mocks
        download_mock.side_effect = lambda x, y: test_yml.replace(
            test_yml_to_be_downloaded
        )

        # call
        self.resource_manager._handle_env_file_string(url, test_yml_to_be_downloaded)

        # assert
        download_mock.assert_called_once()

        # content of test_yml_to_be_downloaded == content of test_yml
        with open(test_yml_to_be_downloaded) as f:
            content = f.read()

        self.assertEqual("name: test", content)

    def test__handle_env_file_string_valid_path(self):
        test_yml_to_be_copied = Path(self.tmp_dir.name).joinpath("test_cp.yml")
        with open(test_yml_to_be_copied, mode="w") as tmp_file:
            tmp_file.write("""name: test_to_be_copied""")

        # create tmp yml file named test.yml
        test_yml = Path(self.tmp_dir.name).joinpath("test.yml")
        with open(test_yml, mode="w") as tmp_file:
            tmp_file.write("""name: test""")

        # call
        self.resource_manager._handle_env_file_string(
            str(test_yml_to_be_copied), test_yml
        )

        # assert
        with open(test_yml) as f:
            content = f.read()

        self.assertEqual("name: test_to_be_copied", content)

    def test__handle_env_file_string_valid_string(self):
        # create tmp yml file named test.yml
        test_yml = Path(self.tmp_dir.name).joinpath("test.yml")
        with open(test_yml, mode="w") as tmp_file:
            tmp_file.write("""name: test""")

        # call
        self.resource_manager._handle_env_file_string(
            "dependencies: test_to_be_taken\n", test_yml
        )

        # assert
        with open(test_yml) as f:
            content = f.read()

        self.assertEqual("dependencies: test_to_be_taken\n", content)

    def test__handle_env_file_string_error(self):
        with self.assertRaises(TypeError):
            self.resource_manager._handle_env_file_string(1, Path(self.tmp_dir.name))

    def test__handle_env_file_stream_valid(self):
        # create tmp yml file named test.yml
        test_yml = Path(self.tmp_dir.name).joinpath("test.yml")
        with open(test_yml, mode="w") as tmp_file:
            tmp_file.write("""name: test""")

        string_io = StringIO("""dependencies: test_to_be_taken\n""")

        # call
        self.resource_manager._handle_env_file_stream(string_io, test_yml)

        # assert
        with open(test_yml) as f:
            content = f.read()

        self.assertEqual("dependencies: test_to_be_taken\n", content)

    def test__handle_env_file_dict(self):
        # create tmp yml file named test.yml
        test_yml = Path(self.tmp_dir.name).joinpath("test.yml")
        with open(test_yml, mode="w") as tmp_file:
            tmp_file.write("""name: test""")

        # call
        self.resource_manager._handle_env_file_dict(
            {"name": "test_to_be_taken"}, test_yml
        )

        # assert
        with open(test_yml) as f:
            content = f.read()

        self.assertEqual("name: test_to_be_taken\n", content)

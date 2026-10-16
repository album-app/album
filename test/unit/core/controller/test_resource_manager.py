import os
from copy import deepcopy
from io import StringIO
from pathlib import Path
from test.unit.test_unit_core_common import TestCatalogAndCollectionCommon
from unittest.mock import MagicMock, patch

from album.core.controller.resource_manager import ResourceManager
from album.core.model.catalog import Catalog
from album.core.model.default_values import DefaultValues
from album.runner.core.model.solution import Solution


def _create_conda_lock_file(solution_yml, conda_lock_executable):
    # like conda-lock: the lock file is written next to the environment file
    lock_path = Path(solution_yml).parent.joinpath("solution.conda-lock.yml")
    lock_path.write_text("lock of\n" + Path(solution_yml).read_text())
    return lock_path


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
        side_effect=_create_conda_lock_file,
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
        env_file = Path(self.tmp_dir.name).joinpath("env.yml")
        env_file.write_text("dependencies:\n  - python\n")
        write_solution_environment_file = MagicMock(return_value=env_file)
        self.resource_manager.write_solution_environment_file = (
            write_solution_environment_file
        )

        # call — no_conda_lock=False so the lock file path is included
        r = self.resource_manager.write_solution_files(
            catalog, catalog_src_path, self.active_solution, Path("deployPath"), False
        )

        solution_root = Path(catalog_src_path).joinpath(
            self.album_controller.configuration().get_solution_path_suffix_unversioned(
                self.active_solution.coordinates()
            )
        )
        expected = [
            "ymlfile",
            "changelogfile",
            solution_root.joinpath("solution.conda-lock.yml"),
        ]
        # assert
        self.assertListEqual(expected, r)
        # the deploy path is a single file: an environment file cannot come with it
        self.assertIsNone(write_solution_environment_file.call_args[0][2])

    @patch(
        "album.core.controller.resource_manager.create_changelog_file",
        return_value="changelogfile",
    )
    @patch(
        "album.environments.controller.conda_lock_manager.CondaLockManager.create_conda_lock_file",
        side_effect=_create_conda_lock_file,
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
        env_file = Path(self.tmp_dir.name).joinpath("env.yml")
        env_file.write_text("dependencies:\n  - python\n")
        write_solution_environment_file = MagicMock(return_value=env_file)
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

    @patch(
        "album.core.controller.resource_manager.create_changelog_file",
        return_value="changelogfile",
    )
    def test_build_solution_files_skips_hidden_files(self, _):
        # prepare
        catalog_src_path, _ = self.setup_empty_catalog("test_cat")
        catalog = Catalog(
            0,
            "test_cat",
            src=catalog_src_path,
            path=Path(self.tmp_dir.name).joinpath("catalog_cache_path"),
        )
        deploy_dir = Path(self.tmp_dir.name).joinpath("deploy_dir")
        deployed = ["solution.py", "sub/data.txt"]
        not_deployed = [
            ".DS_Store",
            ".git/config",
            "__pycache__/solution.cpython-314.pyc",
            "sub/.hidden",
            "sub/.ipynb_checkpoints/notebook-checkpoint.ipynb",
        ]
        for name in deployed + not_deployed:
            deploy_dir.joinpath(name).parent.mkdir(parents=True, exist_ok=True)
            deploy_dir.joinpath(name).write_text("content")

        # mock
        self.resource_manager._create_yaml_file_in_local_src = MagicMock(
            return_value="ymlfile"
        )

        # call
        r = self.resource_manager.write_solution_files(
            catalog, catalog_src_path, self.active_solution, deploy_dir, True
        )

        # assert: only the visible files are copied into the catalog
        solution_root = Path(catalog_src_path).joinpath(
            self.album_controller.configuration().get_solution_path_suffix_unversioned(
                self.active_solution.coordinates()
            )
        )
        self.assertCountEqual(
            [solution_root.joinpath(name) for name in deployed]
            + ["ymlfile", "changelogfile"],
            r,
        )
        copied = [
            p.relative_to(solution_root).as_posix()
            for p in solution_root.rglob("*")
            if p.is_file()
        ]
        self.assertCountEqual(deployed, copied)
        # the skipped folders are named once, not every file inside them
        self.assertIn(
            "Not deploying hidden files and folders and Python caches: "
            + ", ".join(
                sorted(
                    str(Path(p))
                    for p in [
                        ".DS_Store",
                        ".git",
                        "__pycache__",
                        "sub/.hidden",
                        "sub/.ipynb_checkpoints",
                    ]
                )
            ),
            self.get_logs_as_string(),
        )

    @patch(
        "album.core.controller.resource_manager.create_changelog_file",
        return_value="changelogfile",
    )
    @patch(
        "album.environments.controller.conda_lock_manager.CondaLockManager.create_conda_lock_file",
        side_effect=_create_conda_lock_file,
    )
    def test_build_solution_files_keeps_environment_file_of_solution(
        self, create_conda_lock_file_mock, _
    ):
        # prepare: a solution folder with its environment file
        catalog_src_path, _ = self.setup_empty_catalog("test_cat")
        catalog = Catalog(
            0,
            "test_cat",
            src=catalog_src_path,
            path=Path(self.tmp_dir.name).joinpath("catalog_cache_path"),
        )
        deploy_dir = Path(self.tmp_dir.name).joinpath("deploy_dir")
        deploy_dir.mkdir()
        deploy_dir.joinpath("solution.py").write_text("content")
        env_content = "channels:\n  - conda-forge\ndependencies:\n  - python=3.12\n"
        deploy_dir.joinpath("environment.yml").write_text(env_content)
        self.active_solution.setup().dependencies = {
            "environment_file": "environment.yml"
        }
        self.resource_manager._create_yaml_file_in_local_src = MagicMock(
            return_value="ymlfile"
        )

        # call
        r = self.resource_manager.write_solution_files(
            catalog, catalog_src_path, self.active_solution, deploy_dir, False
        )

        # assert: the environment file is deployed as it is
        solution_root = Path(catalog_src_path).joinpath(
            self.album_controller.configuration().get_solution_path_suffix_unversioned(
                self.active_solution.coordinates()
            )
        )
        self.assertEqual(
            env_content, solution_root.joinpath("environment.yml").read_text()
        )
        # conda-lock got the environment album installs, written outside the deployed files
        locked_yml = Path(create_conda_lock_file_mock.call_args[0][0])
        self.assertNotIn(solution_root, locked_yml.parents)
        lock_file = solution_root.joinpath("solution.conda-lock.yml")
        self.assertIn(lock_file, r)
        self.assertIn("python=3.12", lock_file.read_text())
        self.assertIn(
            DefaultValues.runner_api_package_name.value, lock_file.read_text()
        )

    def test_check_file_dependencies(self):
        folder = Path(self.tmp_dir.name).joinpath("solution")
        folder.mkdir()
        folder.joinpath("environment.yml").write_text("dependencies:\n  - python\n")
        folder.joinpath("resources.yml").write_text("resources:\n  a: {}\n")
        outside = Path(self.tmp_dir.name).joinpath("shared.yml")
        outside.write_text("dependencies:\n  - python\n")

        # existing files, wherever they are, content, urls and other forms pass
        for dependencies in [
            None,
            {},
            {"environment_file": "environment.yml", "resource_file": "resources.yml"},
            {"environment_file": "../shared.yml"},
            {"environment_file": str(outside)},
            {"environment_file": "dependencies:\n  - python\n"},
            {"environment_file": "https://example.org/environment.yml"},
            {"environment_file": {"dependencies": ["python"]}},
            {"environment_file": StringIO("dependencies:\n  - python\n")},
        ]:
            with self.subTest(dependencies=dependencies):
                self.active_solution.setup().dependencies = dependencies
                self.resource_manager.check_file_dependencies(
                    self.active_solution, folder
                )

        # a solution given as a single file has no folder for relative paths
        self.active_solution.setup().dependencies = {"environment_file": str(outside)}
        self.resource_manager.check_file_dependencies(self.active_solution, None)

        for dependency, file, folder_, message in [
            (
                "resource_file",
                "resources.yml",
                None,
                "is a path, so the solution has to be installed and deployed as a folder",
            ),
            ("environment_file", "missing.yml", folder, "does not exist"),
        ]:
            with self.subTest(dependency=dependency, file=file):
                self.active_solution.setup().dependencies = {dependency: file}
                with self.assertRaises(TypeError) as e:
                    self.resource_manager.check_file_dependencies(
                        self.active_solution, folder_
                    )
                self.assertIn(f'{dependency} "{file}" {message}', str(e.exception))

        # only the ones asked for are checked
        self.active_solution.setup().dependencies = {"environment_file": "missing.yml"}
        self.resource_manager.check_file_dependencies(
            self.active_solution, folder, ["resource_file"]
        )

    def test__get_file(self):
        folder = Path(self.tmp_dir.name).joinpath("solution")
        folder.joinpath("envs").mkdir(parents=True)
        folder.joinpath(".conda").mkdir()
        for name in ["environment.yml", "envs/environment.yaml", ".conda/env.yml"]:
            folder.joinpath(name).write_text("dependencies: []\n")
        outside = Path(self.tmp_dir.name).joinpath("shared.yml")
        outside.write_text("dependencies: []\n")

        for file, solution_folder, expected in [
            ("environment.yml", folder, folder.joinpath("environment.yml")),
            ("./environment.yml", folder, folder.joinpath("environment.yml")),
            (
                "envs/environment.yaml",
                folder,
                folder.joinpath("envs", "environment.yaml"),
            ),
            (
                "envs/../environment.yml",
                folder,
                folder.joinpath("envs/../environment.yml"),
            ),
            (".conda/env.yml", folder, folder.joinpath(".conda", "env.yml")),
            # outside the folder of the solution
            ("../shared.yml", folder, folder.joinpath("../shared.yml")),
            (str(outside), folder, outside),
            (str(outside), None, outside),
        ]:
            with self.subTest(file=file):
                self.assertEqual(
                    expected,
                    ResourceManager._get_file(
                        file, solution_folder, "environment_file"
                    ),
                )

    def test__get_file_not_from_working_directory(self):
        folder = Path(self.tmp_dir.name).joinpath("solution")
        folder.mkdir()
        working_directory = Path(self.tmp_dir.name).joinpath("working_directory")
        working_directory.mkdir()
        working_directory.joinpath("environment.yml").write_text("dependencies: []\n")

        cwd = os.getcwd()
        os.chdir(working_directory)
        try:
            with self.assertRaises(TypeError) as e:
                ResourceManager._get_file("environment.yml", folder, "environment_file")
            self.assertIn("does not exist", str(e.exception))

            # the one in the folder of the solution is taken, wherever album runs
            folder.joinpath("environment.yml").write_text("dependencies: []\n")
            self.assertEqual(
                folder.joinpath("environment.yml"),
                ResourceManager._get_file(
                    "environment.yml", folder, "environment_file"
                ),
            )
        finally:
            os.chdir(cwd)

    def test__get_file_invalid(self):
        folder = Path(self.tmp_dir.name).joinpath("solution")
        folder.joinpath("envs").mkdir(parents=True)
        folder.joinpath("environment.txt").write_text("dependencies: []\n")
        folder.joinpath("empty.yml").touch()
        missing = Path(self.tmp_dir.name).joinpath("missing.yml")

        for file, solution_folder, message in [
            (
                "missing.yml",
                folder,
                f"does not exist: there is no file {folder.joinpath('missing.yml')}.",
            ),
            (
                "envs",
                folder,
                f"does not exist: there is no file {folder.joinpath('envs')}.",
            ),
            (str(missing), folder, "does not exist."),
            # a solution given as solution.py alone
            (
                "environment.yml",
                None,
                "is a path, so the solution has to be installed and deployed as a "
                'folder: give the folder that holds solution.py and "environment.yml", '
                "not solution.py alone.",
            ),
            ("environment.txt", folder, "is not a .yml or .yaml file."),
            ("empty.yml", folder, "is empty."),
        ]:
            with self.subTest(file=file):
                with self.assertRaises(TypeError) as e:
                    ResourceManager._get_file(file, solution_folder, "environment_file")
                self.assertEqual(
                    f'environment_file "{file}" {message}', str(e.exception)
                )

    @patch("album.core.controller.resource_manager.download_resource")
    def test_write_solution_env_file(self, download_mock):
        # prepare
        solution_no_env = Solution(self.get_solution_dict_with_dependecies())
        solution_no_env.setup()["dependencies"]["environment_file"] = ""
        expected_content_no_env = (
            """['channels:\\n', '- conda-forge\\n', 'dependencies:\\n', '- python=%s\\n', '- conda-forge::%s=%s\\n', '- conda-forge::setuptools>=59.7.0\\n']"""
            % (
                DefaultValues.default_solution_python_version.value,
                DefaultValues.runner_api_package_name.value,
                DefaultValues.runner_api_package_version.value,
            )
        )
        expected_content = (
            """['channels:\\n', '- conda-forge\\n', 'dependencies:\\n', '- python=3.8\\n', '- pip\\n', '- conda-forge::%s=%s\\n', '- conda-forge::setuptools>=59.7.0\\n', 'name: Dummy-Solution18\\n']"""
            % (
                DefaultValues.runner_api_package_name.value,
                DefaultValues.runner_api_package_version.value,
            )
        )

        expected_content_with_setuptools = (
            """['channels:\\n', '- conda-forge\\n', 'dependencies:\\n', '- python=3.8\\n', '- pip\\n', '- conda-forge::setuptools\\n', '- conda-forge::%s=%s\\n', 'name: Dummy-Solution18\\n']"""
            % (
                DefaultValues.runner_api_package_name.value,
                DefaultValues.runner_api_package_version.value,
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

        solution_env_dict = Solution(self.get_solution_dict_with_dependecies())
        solution_env_dict.setup()["dependencies"]["environment_file"] = {
            "name": "Dummy-Solution18",
            "channels": ["conda-forge"],
            "dependencies": ["python=3.8", "pip"],
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

        # a dict is taken as the content of the environment file
        self.resource_manager.write_solution_environment_file(
            solution_env_dict, Path(self.tmp_dir.name)
        )
        with open(Path(self.tmp_dir.name).joinpath("environment.yml")) as f:
            self.assertEqual(expected_content, repr(f.readlines()))

        with self.assertRaises(TypeError):
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

    def test_handle_resource_file_dependency(self):
        yml = Path(self.tmp_dir.name).joinpath("resources.yml")

        # the content of a resource file is recognized by "resources:"
        self.resource_manager.handle_resource_file_dependency(
            "resources:\n  a: {}\n", yml
        )
        with open(yml, encoding="utf-8") as f:
            self.assertEqual("resources:\n  a: {}\n", f.read())

        # the content of an environment file is not a resource file
        with self.assertRaises(TypeError) as e:
            self.resource_manager.handle_resource_file_dependency(
                "dependencies:\n  - python\n", yml
            )
        self.assertIn(
            "resource_file must either contain the content of the resource file",
            str(e.exception),
        )

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

        # call: the path is relative to the folder of the solution
        self.resource_manager._handle_env_file_string(
            "test_cp.yml", test_yml, solution_folder=Path(self.tmp_dir.name)
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

    def test__handle_env_file_string_valid_path_yaml_extension(self):
        # an environment file on disk may use either YAML extension
        env_file = Path(self.tmp_dir.name).joinpath("environment.yaml")
        with open(env_file, mode="w", encoding="utf-8") as tmp_file:
            tmp_file.write("""name: test_to_be_copied""")
        test_yml = Path(self.tmp_dir.name).joinpath("test.yml")

        # call
        self.resource_manager.handle_env_file_dependency(
            "environment.yaml", test_yml, Path(self.tmp_dir.name)
        )

        # assert
        with open(test_yml, encoding="utf-8") as f:
            content = f.read()

        self.assertEqual("name: test_to_be_copied", content)

    def test__handle_env_file_string_path_unknown_extension(self):
        env_file = Path(self.tmp_dir.name).joinpath("environment.txt")
        with open(env_file, mode="w", encoding="utf-8") as tmp_file:
            tmp_file.write("""name: test""")

        with self.assertRaises(TypeError) as e:
            self.resource_manager._handle_env_file_string(
                "environment.txt",
                Path(self.tmp_dir.name).joinpath("test.yml"),
                solution_folder=Path(self.tmp_dir.name),
            )
        self.assertIn("is not a .yml or .yaml file", str(e.exception))

    def test__append_setuptools_to_yml_keeps_existing_spec(self):
        for spec in [
            "setuptools",
            "setuptools>=60",
            "setuptools<58",
            "setuptools=70.*",
            "setuptools==69.5.1",
            "setuptools!=70.0.0",
            "setuptools~=69.0",
            "setuptools 70.*",
            "setuptools[version='>=60']",
            "conda-forge::setuptools",
            "conda-forge::setuptools>=60",
            # album's own pin, so a second call adds nothing
            "conda-forge::setuptools>=59.7.0",
        ]:
            with self.subTest(spec=spec):
                content = {"dependencies": ["python=3.10", spec]}

                result = ResourceManager._append_setuptools_to_yml(content)

                self.assertEqual(["python=3.10", spec], result["dependencies"])

    def test__append_setuptools_to_yml_appends_pin(self):
        pin = "conda-forge::setuptools>=59.7.0"
        for dependencies in [
            None,
            [],
            ["python=3.10"],
            # other packages whose name only starts with "setuptools"
            ["setuptools-scm"],
            ["setuptools_scm>=8"],
            ["conda-forge::setuptools-git-versioning"],
            # a nested pip list is installed by pip after the conda solve
            ["pip", {"pip": ["setuptools>=60"]}],
        ]:
            with self.subTest(dependencies=dependencies):
                content = {"dependencies": deepcopy(dependencies)}

                result = ResourceManager._append_setuptools_to_yml(content)

                self.assertEqual((dependencies or []) + [pin], result["dependencies"])

        with self.subTest(dependencies="missing"):
            self.assertEqual(
                {"dependencies": [pin]}, ResourceManager._append_setuptools_to_yml({})
            )

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

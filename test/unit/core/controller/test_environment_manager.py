import io
import os
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from test.unit.test_unit_core_common import TestUnitCoreCommon
from unittest.mock import MagicMock, patch

from album.core import __version__ as album_version
from album.core.model.catalog import Catalog
from album.core.model.collection_index import CollectionIndex
from album.core.model.default_values import (
    DEFAULT_SOLUTION_ENV_CONTENT,
    DefaultValues,
)
from album.core.model.resolve_result import ResolveResult
from album.environments.utils.file_operations import get_dict_from_yml
from album.runner.core.model.coordinates import Coordinates
from album.runner.core.model.solution import Solution


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
        "album.core.controller.environment_manager.EnvironmentManager._prepare_env_file"
    )
    def test_install_environment_from_lockfile(
        self,
        mock_prepare_env_file,
    ):
        mock_create_environment_from_lockfile = MagicMock()
        self.environment_manager._environment_handler.create_environment_prefer_lock_file = (
            mock_create_environment_from_lockfile
        )
        # prepare
        self.active_solution._installation._package_path.joinpath(
            "solution.conda-lock.yml"
        ).touch()
        resolve = ResolveResult(
            path=None,
            catalog=self.catalog,
            collection_entry=MagicMock(),
            coordinates=self.active_solution.coordinates(),
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

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager._prepare_env_file"
    )
    def test_install_environment_no_conda_lock(self, _):
        create_environment_prefer_lock_file = MagicMock()
        self.environment_manager._environment_handler.create_environment_prefer_lock_file = (
            create_environment_prefer_lock_file
        )
        package_manager = MagicMock()
        self.environment_manager._environment_handler.get_package_manager = MagicMock(
            return_value=package_manager
        )
        self.active_solution._installation._package_path.joinpath(
            "solution.conda-lock.yml"
        ).touch()
        resolve = ResolveResult(
            path=None,
            catalog=self.catalog,
            collection_entry=MagicMock(),
            coordinates=self.active_solution.coordinates(),
            loaded_solution=self.active_solution,
        )
        resolve.loaded_solution().installation().internal_cache_path = MagicMock(
            return_value=Path(self.tmp_dir.name)
        )

        # call
        self.environment_manager.install_environment(resolve, no_conda_lock=True)

        # assert - solved, not installed from the lock file
        create_environment_prefer_lock_file.assert_not_called()
        package_manager.install.assert_called_once()
        self.assertIn(
            'Not technically replicable, "testid:test:1.0.0": it is installed without its '
            "lock file (--no-conda-lock), its environment is solved now.",
            self.get_logs_as_string(),
        )

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

    def _resolve_result_with_parents(self, *parents):
        """Return a resolve result whose collection entry has the given parent chain.

        Each parent is a (catalog_id, name) pair, the direct parent first.
        """
        parent_entry = None
        for catalog_id, name in reversed(parents):
            parent_entry = CollectionIndex.CollectionSolution(
                {"group": "g", "name": name, "version": "1.0.0"},
                {"catalog_id": catalog_id, "parent": parent_entry},
            )
        return ResolveResult(
            path=None,
            catalog=self.catalog,
            collection_entry=CollectionIndex.CollectionSolution(
                {"group": "testid", "name": "test", "version": "1.0.0"},
                {"catalog_id": "testid", "parent": parent_entry},
            ),
            coordinates=self.active_solution.coordinates(),
            loaded_solution=self.active_solution,
        )

    def test_set_environment(self):
        # a solution without a parent runs in its own environment
        environment = self.environment_manager.set_environment(
            self._resolve_result_with_parents()
        )

        self.assertEqual("testname_testid_test_1.0.0", environment.name())
        self.assertEqual(
            environment.path(),
            self.active_solution.installation().environment_path(),
        )

    @patch("album.core.controller.collection.catalog_handler.CatalogHandler.get_by_id")
    def test_set_environment_parent(self, get_by_id):
        get_by_id.side_effect = lambda catalog_id: Catalog(
            catalog_id, "catalog%s" % catalog_id, "path"
        )

        # a solution with a parent runs in the environment of the parent
        environment = self.environment_manager.set_environment(
            self._resolve_result_with_parents((1, "parent"))
        )

        self.assertEqual("catalog1_g_parent_1.0.0", environment.name())
        get_by_id.assert_called_once_with(1)

    @patch("album.core.controller.collection.catalog_handler.CatalogHandler.get_by_id")
    def test_set_environment_parent_with_parent(self, get_by_id):
        get_by_id.side_effect = lambda catalog_id: Catalog(
            catalog_id, "catalog%s" % catalog_id, "path"
        )

        # the parent has a parent itself, so it has no environment: the solution runs
        # in the one of the solution at the top of the chain. It used to get the
        # environment name of its direct parent, which does not exist (#264).
        environment = self.environment_manager.set_environment(
            self._resolve_result_with_parents((1, "parent"), (2, "grandparent"))
        )

        self.assertEqual("catalog2_g_grandparent_1.0.0", environment.name())
        get_by_id.assert_called_once_with(2)

    def _check_album_in_album_logs(self, dependencies, allow_recursive=False):
        """Run the album-in-album check and return the log lines it adds."""
        before = len(self.get_logs())
        self.environment_manager._check_album_in_album(
            {"dependencies": dependencies}, allow_recursive
        )
        return "\n".join(self.get_logs()[before:])

    def test__check_album_in_album(self):
        running = album_version
        no_album = [
            None,
            [],
            ["python=3.10"],
            ["album-solution-api=0.7.1", "albumentations", "conda-forge::album-gui"],
            [{"pip": ["album-gui", "albumentations==1.0", "--index-url https://x"]}],
        ]
        # album without a version, or exactly the running one: allowed with a warning
        same_version = [
            "album",
            "conda-forge/label/dev::album",
            "album=%s" % running,
            "album==%s" % running,
            "album %s" % running,
            "album %s py_0" % running,
            "album=%s=py_0" % running,
            "conda-forge::album=%s" % running,
            "album[version='%s']" % running,
            {"pip": ["album"]},
            {"pip": ["album==%s" % running]},
        ]
        # any other version spec: rejected without allow_recursive
        other_version = [
            "album=0.1.0",
            "album==0.1.0",
            "album>=0.1.0",
            "album<1",
            "album 0.1.0",
            "album=0.1.*",
            "conda-forge::album=0.1.0",
            "album[version='>=0.1']",
            {"pip": ["album==0.1.0"]},
            {"pip": ["album>=0.1.0"]},
            {"pip": ["album~=%s" % running]},  # a range, may install another version
            {"pip": ["album @ git+https://gitlab.com/album-app/album.git"]},
        ]

        for dependencies in no_album:
            with self.subTest(dependencies=dependencies):
                logs = self._check_album_in_album_logs(dependencies)
                self.assertNotIn("Album is planned", logs)

        for dependency in same_version:
            with self.subTest(dependency=dependency):
                logs = self._check_album_in_album_logs(["python=3.10", dependency])
                self.assertIn(
                    "sharing the same database! Only proceed if you know what you are doing!",
                    logs,
                )

        for dependency in other_version:
            with self.subTest(dependency=dependency):
                with self.assertRaises(ValueError) as context:
                    self._check_album_in_album_logs(["python=3.10", dependency])
                self.assertIn("running album %s" % running, str(context.exception))
                self.assertIn(
                    "set allow_recursive during installation", str(context.exception)
                )

                logs = self._check_album_in_album_logs(
                    ["python=3.10", dependency], allow_recursive=True
                )
                self.assertIn(
                    "Potentially incompatible installation of album in album detected!",
                    logs,
                )

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
        self.environment_manager._prepare_env_file(
            None, Path(self.tmp_dir.name), None, None
        )

    def test__prepare_env_file_empty_deps(self):
        self.environment_manager._prepare_env_file(
            {}, Path(self.tmp_dir.name), None, None
        )

    def test__prepare_env_file_default_environment_excludes_defaults_channel(self):
        r = self.environment_manager._prepare_env_file(
            None, Path(self.tmp_dir.name), "env_name", None
        )

        channels = get_dict_from_yml(r)["channels"]
        self.assertEqual(["conda-forge", "nodefaults"], channels)
        # the shared content, which deploy hands to conda-lock, stays without it
        self.assertEqual(["conda-forge"], DEFAULT_SOLUTION_ENV_CONTENT["channels"])

    def test__prepare_env_file_solution_environment_keeps_its_channels(self):
        env_file = {"channels": ["bioconda", "conda-forge"], "dependencies": []}

        r = self.environment_manager._prepare_env_file(
            {"environment_file": env_file}, Path(self.tmp_dir.name), "env_name", None
        )

        channels = get_dict_from_yml(r)["channels"]
        self.assertEqual(["bioconda", "conda-forge"], channels)

    @patch(
        "album.core.controller.environment_manager.create_path_recursively",
        return_value="createdPath",
    )
    def test__prepare_env_file_invalid_file(self, create_path_mock):
        with self.assertRaises(TypeError) as context:
            self.environment_manager._prepare_env_file(
                {"environment_file": "env_file"},
                Path(self.closed_tmp_file.name),
                None,
                None,
            )
            self.assertIn("Yaml file must either be a url", str(context.exception))

        create_path_mock.assert_called_once()

    @patch(
        "album.core.controller.environment_manager.create_path_recursively",
        return_value="createdPath",
    )
    def test__prepare_env_file_valid_file(self, create_path_mock):

        # create tmp yml file named test.yml
        test_yml = Path(self.tmp_dir.name).joinpath("test.yml")
        with open(test_yml, mode="w") as tmp_file:
            tmp_file.write("""name: test""")

        r = self.environment_manager._prepare_env_file(
            {"environment_file": "test.yml"},
            Path(self.tmp_dir.name),
            "env_name",
            None,
            solution_folder=Path(self.tmp_dir.name),
        )

        self.assertEqual(Path(self.tmp_dir.name).joinpath("env_name.yml"), r)

        create_path_mock.assert_called_once()

    def test_create_environment_environment_file_from_package_path(self):
        # an installed solution: its files are in its package path
        package_path = Path(self.tmp_dir.name).joinpath("package")
        package_path.mkdir()
        package_path.joinpath("environment.yml").write_text(
            "channels:\n  - bioconda\ndependencies:\n  - python=3.12\n"
        )
        cache = Path(self.tmp_dir.name).joinpath("cache")
        create_environment = MagicMock()
        self.environment_manager._environment_handler.create_environment_prefer_lock_file = (
            create_environment
        )

        self.environment_manager.create_environment(
            cache,
            {"environment_file": "environment.yml"},
            "env_name",
            "0.7.3",
            package_path,
            solution_folder=package_path,
        )

        environment_file = create_environment.call_args[0][0].yaml_file()
        self.assertEqual(["bioconda"], get_dict_from_yml(environment_file)["channels"])

    def test_create_environment_environment_written_by_deploy(self):
        # a deployed solution: the environment file it names is not on this computer
        package_path = Path(self.tmp_dir.name).joinpath("package")
        package_path.mkdir()
        framework = (
            "conda-forge::%s=0.7.1" % DefaultValues.runner_api_package_name.value
        )
        package_path.joinpath("solution.environment.yml").write_text(
            "channels:\n  - bioconda\ndependencies:\n  - python=3.12\n  - %s\n"
            % framework
        )
        create_environment = MagicMock()
        self.environment_manager._environment_handler.create_environment_prefer_lock_file = (
            create_environment
        )

        self.environment_manager.create_environment(
            Path(self.tmp_dir.name).joinpath("cache"),
            {"environment_file": "/not/on/this/computer/environment.yml"},
            "env_name",
            "0.7.1",
            package_path,
            solution_folder=package_path,
        )

        # taken as it is, album-solution-api is in it already
        environment = get_dict_from_yml(create_environment.call_args[0][0].yaml_file())
        self.assertEqual("env_name", environment["name"])
        self.assertEqual(["bioconda"], environment["channels"])
        self.assertEqual(["python=3.12", framework], environment["dependencies"])

    def test_create_environment_no_conda_lock(self):
        # deployed with a lock file, installed without it
        package_path = Path(self.tmp_dir.name).joinpath("package")
        package_path.mkdir()
        package_path.joinpath("solution.conda-lock.yml").write_text("lock")
        package_path.joinpath("solution.environment.yml").write_text(
            "channels:\n  - bioconda\ndependencies:\n  - python=3.12\n"
        )
        create_environment_prefer_lock_file = MagicMock()
        self.environment_manager._environment_handler.create_environment_prefer_lock_file = (
            create_environment_prefer_lock_file
        )
        package_manager = MagicMock()
        self.environment_manager._environment_handler.get_package_manager = MagicMock(
            return_value=package_manager
        )

        self.environment_manager.create_environment(
            Path(self.tmp_dir.name).joinpath("cache"),
            {"environment_file": "/not/on/this/computer/environment.yml"},
            "env_name",
            "0.7.1",
            package_path,
            solution_folder=package_path,
            no_conda_lock=True,
        )

        # solved from the environment it locked
        create_environment_prefer_lock_file.assert_not_called()
        environment = get_dict_from_yml(
            package_manager.install.call_args[0][0].yaml_file()
        )
        self.assertEqual(["python=3.12"], environment["dependencies"])

    def test_create_environment_lock_file_does_not_install(self):
        package_path = Path(self.tmp_dir.name).joinpath("package")
        package_path.mkdir()
        package_path.joinpath("solution.environment.yml").write_text(
            "dependencies:\n  - python=3.12\n"
        )
        # as album-environments fails, the output of the command is in the log
        self.environment_manager._environment_handler.create_environment_prefer_lock_file = MagicMock(
            side_effect=RuntimeError(
                "Command failed due to: ERROR while running conda-lock install"
            )
        )
        args = (
            Path(self.tmp_dir.name).joinpath("cache"),
            None,
            "env_name",
            "0.7.1",
            package_path,
        )

        # no lock file: the error as it is
        with self.assertRaises(RuntimeError) as e:
            self.environment_manager.create_environment(*args)
        self.assertEqual(
            "Command failed due to: ERROR while running conda-lock install",
            str(e.exception),
        )

        # from the lock file: the error names --no-conda-lock
        package_path.joinpath("solution.conda-lock.yml").write_text("lock")
        with self.assertRaises(RuntimeError) as e:
            self.environment_manager.create_environment(*args)
        self.assertEqual(
            "Installing the environment from the lock file failed: Command failed due "
            "to: ERROR while running conda-lock install. If the lock file does not "
            "install on this system, install the solution with --no-conda-lock to "
            "solve its environment instead.",
            str(e.exception),
        )

    def test__prepare_env_file_environment_written_by_deploy_album_in_album(self):
        snapshot = Path(self.tmp_dir.name).joinpath("solution.environment.yml")
        snapshot.write_text("dependencies:\n  - album=0.0.1\n")

        # the album-in-album check applies to it as well
        with self.assertRaises(ValueError):
            self.environment_manager._prepare_env_file(
                None,
                Path(self.tmp_dir.name),
                "env_name",
                "0.7.1",
                environment_snapshot=snapshot,
            )

    def test_check_album_version(self):
        folder = Path(self.tmp_dir.name).joinpath("solution")
        folder.mkdir()
        solution = Solution(
            dict(
                self.get_solution_dict(),
                dependencies={"environment_file": "environment.yml"},
            )
        )
        resolve = ResolveResult(
            path=folder.joinpath("solution.py"),
            catalog=self.catalog,
            collection_entry=None,
            coordinates=solution.coordinates(),
            loaded_solution=solution,
        )

        # none, an unversioned one or the running one
        for dependencies in ["python", "album", "album=%s" % album_version]:
            with self.subTest(dependencies=dependencies):
                folder.joinpath("environment.yml").write_text(
                    "dependencies:\n  - %s\n" % dependencies
                )
                self.environment_manager.check_album_version(resolve)

        # another album version
        folder.joinpath("environment.yml").write_text(
            "dependencies:\n  - album=0.0.1\n"
        )
        with self.assertRaises(ValueError) as e:
            self.environment_manager.check_album_version(resolve)
        self.assertEqual(
            'its environment installs "album=0.0.1", not the running album %s.'
            % album_version,
            str(e.exception),
        )

        # a deployed solution is installed from the environment album deploy wrote
        folder.joinpath("solution.environment.yml").write_text(
            "dependencies:\n  - python\n"
        )
        self.environment_manager.check_album_version(resolve)

    def test_check_lock_file(self):
        folder = Path(self.tmp_dir.name).joinpath("solution")
        folder.mkdir()
        lock_manager = MagicMock()
        lock_manager.conda_lock_executable.side_effect = RuntimeError(
            "No conda-lock executable found!"
        )
        self.environment_manager._environment_handler.get_conda_lock_manager = (
            MagicMock(return_value=lock_manager)
        )
        coordinates = Coordinates("g", "n", "0.1.0")

        # no lock file, or a single file: solved, conda-lock is not needed
        self.environment_manager.check_lock_file(coordinates, folder)
        self.environment_manager.check_lock_file(coordinates, None)

        # a lock file conda-lock is not found for
        folder.joinpath("solution.conda-lock.yml").write_text("lock")
        with self.assertRaises(RuntimeError) as e:
            self.environment_manager.check_lock_file(coordinates, folder)
        self.assertIn(
            '"g:n:0.1.0" is installed from its lock file, but conda-lock',
            str(e.exception),
        )
        # unless it is solved instead
        self.environment_manager.check_lock_file(
            coordinates, folder, no_conda_lock=True
        )

        # conda-lock found
        lock_manager.conda_lock_executable.side_effect = None
        lock_manager.conda_lock_executable.return_value = "/bin/conda-lock"
        self.environment_manager.check_lock_file(coordinates, folder)

    def _warning_without_lock_file(
        self, lock_file, conda_lock, reasons, no_conda_lock=False
    ):
        package_path = Path(tempfile.mkdtemp(dir=self.tmp_dir.name))
        if lock_file:
            package_path.joinpath("solution.conda-lock.yml").write_text("lock")
        if reasons:
            package_path.joinpath("solution.yml").write_text(
                "replicability:\n  reasons:\n  - it is deployed without a lock file\n"
            )
        lock_manager = MagicMock()
        if conda_lock:
            lock_manager.conda_lock_executable.return_value = conda_lock
        else:
            # as the conda-lock manager of album-environments does
            lock_manager.conda_lock_executable.side_effect = RuntimeError(
                "No conda-lock executable found!"
            )
        self.environment_manager._environment_handler.get_conda_lock_manager = (
            MagicMock(return_value=lock_manager)
        )
        self.captured_output.seek(0)
        self.captured_output.truncate(0)

        self.environment_manager._warn_without_lock_file(
            Coordinates("g", "n", "0.1.0"), package_path, no_conda_lock
        )

        return self.get_logs_as_string()

    def test__warn_without_lock_file(self):
        # installed from the lock file
        self.assertNotIn(
            "WARNING", self._warning_without_lock_file(True, "/bin/conda-lock", False)
        )
        # a lock file conda-lock is not found for: not solved again without it
        with self.assertRaises(RuntimeError) as e:
            self._warning_without_lock_file(True, None, False)
        self.assertEqual(
            '"g:n:0.1.0" is installed from its lock file, but conda-lock, which installs '
            "it, is not found. Set ENVIRONMENT_CONDA_LOCK_PATH to the conda-lock "
            "executable, or install it with --no-conda-lock to solve its environment "
            "instead.",
            str(e.exception),
        )
        # installed without its lock file, so conda-lock is not needed
        self.assertIn(
            'Not technically replicable, "g:n:0.1.0": it is installed without its lock '
            "file (--no-conda-lock), its environment is solved now.",
            self._warning_without_lock_file(True, None, False, no_conda_lock=True),
        )
        # no lock file
        self.assertIn(
            'Not technically replicable, "g:n:0.1.0": it has no lock file, its '
            "environment is solved now.",
            self._warning_without_lock_file(False, "/bin/conda-lock", False),
        )
        # deployed without a lock file: its reasons say so already
        self.assertNotIn(
            "WARNING", self._warning_without_lock_file(False, "/bin/conda-lock", True)
        )

    @patch(
        "album.core.controller.environment_manager.create_path_recursively",
        return_value="createdPath",
    )
    def test__prepare_env_file_valid_url(self, create_path_mock):
        # create tmp yml file named test.yml
        test_yml = Path(self.tmp_dir.name).joinpath("unittest.yml")
        with open(test_yml, mode="w") as tmp_file:
            tmp_file.write("""name: test""")

        handle_env_file_dependency_mock = MagicMock(return_value=test_yml)
        self.album_controller.resource_manager().handle_env_file_dependency = (
            handle_env_file_dependency_mock
        )

        url = "http://test.de"

        r = self.environment_manager._prepare_env_file(
            {"environment_file": url}, test_yml.parent, self.test_environment_name, None
        )

        self.assertEqual(
            test_yml.parent.joinpath(self.test_environment_name + ".yml"), r
        )

        create_path_mock.assert_called_once()
        handle_env_file_dependency_mock.assert_called_once()

    @patch(
        "album.core.controller.environment_manager.create_path_recursively",
        return_value="createdPath",
    )
    def test__prepare_env_file_invalid_StringIO(self, create_path_mock):
        _cache_path = Path(tempfile.gettempdir())

        string_io = io.StringIO("""testStringIo""")

        with self.assertRaises(TypeError):
            r = self.environment_manager._prepare_env_file(
                {"environment_file": string_io},
                _cache_path,
                self.test_environment_name,
                None,
            )

        create_path_mock.assert_called_once()

    @patch(
        "album.core.controller.environment_manager.create_path_recursively",
        return_value="createdPath",
    )
    def test__prepare_env_file_valid_StringIO(self, create_path_mock):
        _cache_path = Path(tempfile.gettempdir())

        string_io = io.StringIO("""name: value""")

        r = self.environment_manager._prepare_env_file(
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


class TestEnvironmentManagerFrameworkCheck(TestUnitCoreCommon):
    """Tests for the framework sanity check, independent of any package manager."""

    def setUp(self):
        super().setUp()
        # the check only concerns the configured package name, so do not set up
        # a package manager (no micromamba download, no network access)
        with patch(
            "album.core.controller.environment_manager.init_environment_handler"
        ):
            self.environment_manager = self.album_controller.environment_manager()

    def test__append_framework_to_dependencies_ignores_cwd(self):
        # a folder named like the runner package in the current working directory
        # (e.g. a checkout of album-solution-api) must not be mistaken for a
        # "folder" framework definition
        framework_name = DefaultValues.runner_api_package_name.value
        cwd = os.getcwd()
        os.chdir(self.tmp_dir.name)
        try:
            Path(framework_name).mkdir()
            r = self.environment_manager._append_framework_to_dependencies(
                {"dependencies": ["python=3.10"]}, "0.7.1", framework_name
            )
        finally:
            os.chdir(cwd)

        self.assertEqual(
            ["python=3.10", "conda-forge::%s=0.7.1" % framework_name],
            r["dependencies"],
        )

    @patch("album.core.controller.environment_manager.DefaultValues")
    def test__append_framework_to_dependencies_invalid_name(self, default_values):
        for framework_name in [
            "path/to/album-solution-api",
            "album-solution-api.zip",
            "https://example.org/album-solution-api",
        ]:
            with self.subTest(framework_name=framework_name):
                default_values.runner_api_package_name.value = framework_name
                with self.assertRaises(ValueError) as context:
                    self.environment_manager._append_framework_to_dependencies(
                        {"dependencies": []}, "0.7.1", framework_name
                    )
                self.assertIn(
                    "Framework is not properly defined", str(context.exception)
                )

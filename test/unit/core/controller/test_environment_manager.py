import io
import os
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from test.unit.test_unit_core_common import TestUnitCoreCommon
from unittest.mock import MagicMock, patch

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
            {"environment_file": str(test_yml)},
            Path(self.tmp_dir.name),
            "env_name",
            None,
        )

        self.assertEqual(Path(self.tmp_dir.name).joinpath("env_name.yml"), r)

        create_path_mock.assert_called_once()

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

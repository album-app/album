from pathlib import Path
from test.integration.test_integration_core_common import TestIntegrationCoreCommon
from unittest.mock import MagicMock

from album.core.model.resolve_result import ResolveResult


class TestIntegrationEnvironmentPreparation(TestIntegrationCoreCommon):
    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    def _set_resolve_result(self, loaded_solution):
        class FakeCat:
            def name(self):
                return "fake"

        return ResolveResult(
            path=Path(self.tmp_dir.name),
            catalog=FakeCat(),
            collection_entry=None,
            loaded_solution=loaded_solution,
            coordinates=loaded_solution.coordinates(),
        )

    def _setup(self):
        mock_create_environment_prefer_lock_file = MagicMock()
        self.album_controller.environment_manager().get_environment_handler().create_environment_prefer_lock_file = (
            mock_create_environment_prefer_lock_file
        )

        loaded_solution = self.album_controller.state_manager().load(
            self.get_test_solution_path()
        )
        loaded_solution.installation().set_package_path(Path(self.tmp_dir.name))
        loaded_solution.installation().set_installation_path(Path(self.tmp_dir.name))

        return loaded_solution

    def test_album_in_album_unversioned(self):
        loaded_solution = self._setup()

        dependencies_album_unversioned = {
            "channels": ["conda-forge"],
            "dependencies": ["python=3.8.5", "album"],
        }

        # dependencies album unversioned
        loaded_solution._setup["dependencies"] = {
            "environment_file": dependencies_album_unversioned
        }
        solution = self._set_resolve_result(loaded_solution)

        # call
        self.album_controller.environment_manager().install_environment(solution)

        # assert warning
        self.assertIn(
            "Only proceed if you know what you are doing",
            self.get_logs()[-1],
        )

    def test_album_in_album_versioned(self):
        loaded_solution = self._setup()

        dependencies_album_versioned = {
            "channels": ["conda-forge"],
            "dependencies": ["python=3.8.5", "album==0.1.0"],
        }

        # dependencies album versioned
        loaded_solution._setup["dependencies"] = {
            "environment_file": dependencies_album_versioned
        }
        solution = self._set_resolve_result(loaded_solution)

        # call
        with self.assertRaises(ValueError):
            self.album_controller.environment_manager().install_environment(solution)

    def test_album_in_album_pip_versioned(self):
        loaded_solution = self._setup()

        dependencies_album_pip_versioned = {
            "channels": ["conda-forge"],
            "dependencies": ["python=3.8.5", "pip", {"pip": ["album==0.1.0"]}],
        }

        # pip dependencies album versioned
        loaded_solution._setup["dependencies"] = {
            "environment_file": dependencies_album_pip_versioned
        }
        solution = self._set_resolve_result(loaded_solution)

        # call
        with self.assertRaises(ValueError):
            self.album_controller.environment_manager().install_environment(solution)

    def test_album_in_album_pip_unversioned(self):
        loaded_solution = self._setup()

        dependencies_album_pip_unversioned = {
            "channels": ["conda-forge"],
            "dependencies": ["python=3.8.5", "pip", {"pip": ["album"]}],
        }

        # pip dependencies album unversioned
        loaded_solution._setup["dependencies"] = {
            "environment_file": dependencies_album_pip_unversioned
        }
        solution = self._set_resolve_result(loaded_solution)

        # call
        self.album_controller.environment_manager().install_environment(solution)

        # assert warning
        self.assertIn(
            "Only proceed if you know what you are doing",
            self.get_logs()[-1],
        )

    def test_no_album_in_album(self):
        loaded_solution = self._setup()

        dependencies_no_album = {
            "channels": ["conda-forge"],
            "dependencies": ["python=3.8.5"],
        }

        # dependencies no album
        loaded_solution._setup["dependencies"] = {
            "environment_file": dependencies_no_album
        }
        solution = self._set_resolve_result(loaded_solution)

        # call
        self.album_controller.environment_manager().install_environment(solution)

        # assert no warning
        self.assertNotIn(
            "set allow_recursive during installation",
            self.get_logs(),
        )

    def test_album_in_album_pip_versioned_allow_recursive(self):
        loaded_solution = self._setup()

        dependencies_album_pip_versioned = {
            "channels": ["conda-forge"],
            "dependencies": ["python=3.8.5", "pip", {"pip": ["album==0.1.0"]}],
        }

        # pip dependencies album versioned
        loaded_solution._setup["dependencies"] = {
            "environment_file": dependencies_album_pip_versioned
        }
        solution = self._set_resolve_result(loaded_solution)

        # call
        self.album_controller.environment_manager().install_environment(
            solution, allow_recursive=True
        )

        # assert warning
        self.assertIn(
            "Potentially unsafe installation of album in album detected!",
            self.get_logs()[-1],
        )

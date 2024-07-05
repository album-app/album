from pathlib import Path
from test.integration.test_integration_core_common import TestIntegrationCoreCommon
from unittest.mock import MagicMock

from album.core.model.resolve_result import ResolveResult


class TestIntegrationEnvironmentPreparation(TestIntegrationCoreCommon):
    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    def test_album_in_album_warning(self):
        mock_create_environment_prefer_lock_file = MagicMock()
        self.album_controller.environment_manager().get_environment_handler().create_environment_prefer_lock_file = (
            mock_create_environment_prefer_lock_file
        )

        dependencies_album_unversioned = {
            "channels": ["conda-forge"],
            "dependencies": ["python=3.8.5", "album"],
        }
        dependencies_album_versioned = {
            "channels": ["conda-forge"],
            "dependencies": ["python=3.8.5", "album==0.1.0"],
        }
        dependencies_album_pip_versioned = {
            "channels": ["conda-forge"],
            "dependencies": ["python=3.8.5", "pip", {"pip": ["album==0.1.0"]}],
        }
        dependencies_album_pip_unversioned = {
            "channels": ["conda-forge"],
            "dependencies": ["python=3.8.5", "pip", {"pip": ["album"]}],
        }

        class FakeCat:
            def name(self):
                return "fake"

        def _set_resolve_result(sol):
            return ResolveResult(
                path=Path(self.tmp_dir.name),
                catalog=FakeCat(),
                collection_entry=None,
                loaded_solution=loaded_solution,
                coordinates=loaded_solution.coordinates(),
            )

        loaded_solution = self.album_controller.state_manager().load(
            self.get_test_solution_path()
        )
        loaded_solution.installation().set_package_path(Path(self.tmp_dir.name))
        loaded_solution.installation().set_installation_path(Path(self.tmp_dir.name))

        # dependencies album unversioned
        loaded_solution._setup["dependencies"] = {
            "environment_file": dependencies_album_unversioned
        }
        solution = _set_resolve_result(loaded_solution)

        # call
        self.album_controller.environment_manager().install_environment(solution)

        # assert warning
        self.assertIn(
            "Only proceed if you know what you are doing",
            self.captured_output.getvalue(),
        )

        # dependencies album versioned
        loaded_solution._setup["dependencies"] = {
            "environment_file": dependencies_album_versioned
        }
        solution = _set_resolve_result(loaded_solution)

        # call
        with self.assertRaises(ValueError):
            self.album_controller.environment_manager().install_environment(solution)

        # pip dependencies album versioned
        loaded_solution._setup["dependencies"] = {
            "environment_file": dependencies_album_pip_versioned
        }
        solution = _set_resolve_result(loaded_solution)

        # call
        with self.assertRaises(ValueError):
            self.album_controller.environment_manager().install_environment(solution)

        # pip dependencies album unversioned
        loaded_solution._setup["dependencies"] = {
            "environment_file": dependencies_album_pip_unversioned
        }
        solution = _set_resolve_result(loaded_solution)

        # call
        self.album_controller.environment_manager().install_environment(solution)

        # assert warning
        self.assertIn(
            "Only proceed if you know what you are doing",
            self.captured_output.getvalue(),
        )

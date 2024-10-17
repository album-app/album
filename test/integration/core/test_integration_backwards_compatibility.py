from test.integration.test_integration_core_common import TestIntegrationCoreCommon
from unittest.mock import MagicMock, patch

from album.core.model.default_values import DefaultValues


class TestIntegrationBackwardsCompatibility(TestIntegrationCoreCommon):
    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    class EnumFake:
        def __init__(self, name, value):
            self.name = name
            self.value = value

    @patch("album.core.controller.environment_manager.DefaultValues", autospec=True)
    def test_ensure_backwards_compatibility(self, df_mock):
        # set the default values for the runner api package version to None
        for x in DefaultValues:
            if x.name.startswith("runner_api_package_version"):
                setattr(
                    df_mock,
                    x.name,
                    TestIntegrationBackwardsCompatibility.EnumFake(x.name, None),
                )
            else:
                setattr(
                    df_mock,
                    x.name,
                    TestIntegrationBackwardsCompatibility.EnumFake(x.name, x.value),
                )

        self.album_controller.migration_manager().is_outdated_core = MagicMock()
        self.album_controller.migration_manager().is_outdated_api = MagicMock(
            return_value=True
        )

        # install an environment that holds the old album api version
        solution_path = self.get_test_solution_path(
            "solution21_backwards_compatibility.py"
        )
        solution = self.album_controller.collection_manager().resolve_and_load(
            solution_path
        )

        # explicitly do not install the solution api version in the environment
        solution.loaded_solution().setup().album_api_version = ""

        self.album_controller.install_manager()._install_loaded_resolve_result(
            resolve_result=solution, parent=False, allow_unsafe=False
        )
        output_dict_as_str = self.captured_output.getvalue()

        self.assertIn(
            "Install backwards compatibility solution",
            output_dict_as_str,
            "Your install routine has not been called! Backwards compatibility broken!",
        )

        # run the solution
        self.album_controller.run_manager().run(solution_path)
        output_dict_as_str = self.captured_output.getvalue()

        self.assertIn(
            "Run backwards compatibility solution",
            output_dict_as_str,
            "Your run routine has not been called! Backwards compatibility broken!",
        )

        # test the solution
        self.album_controller.test_manager().test(solution_path)
        output_dict_as_str = self.captured_output.getvalue()

        self.assertIn(
            "Pre test backwards compatibility solution",
            output_dict_as_str,
            "Your test routine has not been called! Backwards compatibility broken!",
        )
        self.assertIn(
            "Test backwards compatibility solution",
            output_dict_as_str,
            "Your test routine has not been called! Backwards compatibility broken!",
        )

        # uninstall the solution
        self.album_controller.install_manager().uninstall(solution_path)

        output_dict_as_str = self.captured_output.getvalue()

        self.assertIn(
            "Uninstall backwards compatibility solution",
            output_dict_as_str,
            "Your uninstall routine has not been called! Backwards compatibility broken!",
        )

    @patch("album.core.controller.environment_manager.DefaultValues", autospec=True)
    def test_ensure_backwards_compatibility_parent(self, df_mock):
        # set the default values for the runner api package version to None
        for x in DefaultValues:
            if x.name.startswith("runner_api_package_version"):
                setattr(
                    df_mock,
                    x.name,
                    TestIntegrationBackwardsCompatibility.EnumFake(x.name, None),
                )
            else:
                setattr(
                    df_mock,
                    x.name,
                    TestIntegrationBackwardsCompatibility.EnumFake(x.name, x.value),
                )

        self.album_controller.migration_manager().is_outdated_core = MagicMock()
        self.album_controller.migration_manager().is_outdated_api = MagicMock(
            return_value=True
        )

        # install parent
        solution_path = self.get_test_solution_path(
            "solution21_backwards_compatibility_parent.py"
        )
        solution = self.album_controller.collection_manager().resolve_and_load(
            solution_path
        )

        # explicitly do not install the solution api version in the environment
        solution.loaded_solution().setup().album_api_version = ""

        self.album_controller.install_manager()._install_loaded_resolve_result(
            resolve_result=solution, parent=False, allow_unsafe=False
        )

        # install child, environment used from parent, framework installed via parent
        solution_path = self.get_test_solution_path(
            "solution21_backwards_compatibility_with_parent.py"
        )
        solution = self.album_controller.collection_manager().resolve_and_load(
            solution_path
        )
        self.album_controller.install_manager()._install_loaded_resolve_result(
            resolve_result=solution, parent=False, allow_unsafe=False
        )

        # run the solution
        self.album_controller.run_manager().run(solution_path)
        output_dict_as_str = self.captured_output.getvalue()

        self.assertIn(
            "Run backwards compatibility solution with parent",
            output_dict_as_str,
            "Your run routine has not been called! Backwards compatibility broken!",
        )

        # test the solution
        self.album_controller.test_manager().test(solution_path)
        output_dict_as_str = self.captured_output.getvalue()

        self.assertIn(
            "Pre test backwards compatibility solution with parent",
            output_dict_as_str,
            "Your test routine has not been called! Backwards compatibility broken!",
        )
        self.assertIn(
            "Test backwards compatibility solution with parent",
            output_dict_as_str,
            "Your test routine has not been called! Backwards compatibility broken!",
        )

        # uninstall the solution
        self.album_controller.install_manager().uninstall(solution_path)

        output_dict_as_str = self.captured_output.getvalue()

        self.assertIn(
            "Uninstall backwards compatibility solution with parent",
            output_dict_as_str,
            "Your uninstall routine has not been called! Backwards compatibility broken!",
        )

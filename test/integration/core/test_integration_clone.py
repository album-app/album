from pathlib import Path

from album.core.model.default_values import DefaultValues
from album.core.utils.operations.git_operations import clone_repository, create_bare_repository
from test.integration.test_integration_core_common import TestIntegrationCoreCommon


class TestIntegrationClone(TestIntegrationCoreCommon):

    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    def test_clone_solution(self):
        input_path = self.get_test_solution_path("solution0_dummy_no_routines.py")
        self.fake_install(input_path)
        target_dir = Path(self.tmp_dir.name).joinpath("my_catalog")

        # run
        self.album_controller.clone_manager().clone(input_path, target_dir=str(target_dir), name="my_solution")

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertTrue(target_dir.joinpath("my_solution", DefaultValues.solution_default_name.value).exists())

    def test_clone_solution_template(self):
        target_dir = Path(self.tmp_dir.name).joinpath("my_catalog")

        # add smth. to clone from
        self.fake_install(self.get_test_solution_path(), create_environment=False)

        # run
        self.album_controller.clone_manager().clone("group:name:0.1.0", target_dir=str(target_dir),
                                                    name="my_solution")

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertTrue(target_dir.joinpath("my_solution", DefaultValues.solution_default_name.value).exists())

    def test_clone_catalog_template(self):
        target_path = Path(self.tmp_dir.name).joinpath("my_catalogs", "my_catalog")

        # run
        self.album_controller.clone_manager().clone("template:catalog", target_dir=str(target_path), name="my_catalog")

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertIn(
            "Initialized new catalog \"my_catalog\" from template \"catalog\" in %s" % target_path,
            self.captured_output.getvalue()
        )
        with clone_repository(target_path, Path(self.tmp_dir.name).joinpath("tmp_repo")) as repo:
            self.assertTrue(Path(repo.working_tree_dir).joinpath("album_catalog_index.json").exists())

    def test_clone_catalog_template_into_existing_repo(self):
        target_path = Path(self.tmp_dir.name).joinpath("my_catalogs", "my_catalog")
        create_bare_repository(target_path)

        # run
        self.album_controller.clone_manager().clone("template:catalog", target_dir=str(target_path), name="my_catalog",
                                                        git_email=DefaultValues.catalog_git_email.value,
                                                        git_name=DefaultValues.catalog_git_user.value)

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertIn(
            "Initialized new catalog \"my_catalog\" from template \"catalog\" in %s" % target_path,
            self.captured_output.getvalue()
        )
        with clone_repository(target_path, Path(self.tmp_dir.name).joinpath("tmp_repo")) as repo:
            self.assertTrue(Path(repo.working_tree_dir).joinpath("album_catalog_index.json").exists())

    def test_clone_non_existing_solution(self):
        # run
        with self.assertRaises(LookupError) as e:
            self.album_controller.clone_manager().clone("weirdPath", target_dir=str(Path(self.tmp_dir.name)),
                                                        name="my_solution")

        self.assertIn("Cannot find solution", e.exception.args[0])

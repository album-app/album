import unittest
from pathlib import Path

from album.core.model.default_values import DefaultValues
from test.integration.test_integration_core_common import TestIntegrationCoreCommon


class TestIntegrationClone(TestIntegrationCoreCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_clone_solution(self):
        input_path = self.get_test_solution_path("solution0_dummy_no_routines.py")
        self.fake_install(input_path)
        target_dir = Path(self.tmp_dir.name).joinpath("my_catalog")

        # run
        self.album_instance.clone_manager().clone(input_path, target_dir=str(target_dir), name="my_solution")

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        # FIXME this assertion fails because resolving the input path points to a different solution path in a temp download dir
        # self.assertIn(f"INFO - Copied solution {str(input_path)} to {self.tmp_dir.name}/my_catalog/my_solution/solution.py", self.captured_output.getvalue())
        self.assertTrue(target_dir.joinpath("my_solution", DefaultValues.solution_default_name.value).exists())

    def test_clone_solution_template(self):
        target_dir = Path(self.tmp_dir.name).joinpath("my_catalog")

        # run
        self.album_instance.clone_manager().clone("album:template-r:0.1.0-SNAPSHOT", target_dir=str(target_dir), name="my_solution")

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertTrue(target_dir.joinpath("my_solution", DefaultValues.solution_default_name.value).exists())

    def test_clone_catalog_template(self):
        target_dir = Path(self.tmp_dir.name).joinpath("my_catalogs")

        # run
        self.album_instance.clone_manager().clone("template:catalog", target_dir=str(target_dir), name="my_catalog")

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        target_path = Path(self.tmp_dir.name).joinpath("my_catalogs", "my_catalog")
        self.assertIn(
            f"INFO - Downloaded template from https://gitlab.com/album-app/catalogs/templates/catalog/-/archive/main/catalog-main.zip to {str(target_path)}",
            self.captured_output.getvalue())
        self.assertTrue(target_path.joinpath("album_catalog_index.json").exists())
        self.assertTrue(target_path.joinpath("album_solution_list.json").exists())

    def test_clone_non_existing_solution(self):
        # run
        with self.assertRaises(ValueError) as e:
            self.album_instance.clone_manager().clone("weirdPath", target_dir=str(Path(self.tmp_dir.name)), name="my_solution")

        self.assertIn("Invalid input format!", e.exception.args[0])


if __name__ == '__main__':
    unittest.main()

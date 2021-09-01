import sys
import unittest
from pathlib import Path

from album.argument_parsing import main
from album.core.model.default_values import DefaultValues
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationClone(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_clone_solution(self):

        input_path = self.get_test_solution_path("solution0_dummy_no_routines.py")
        self.fake_install(input_path)
        target_dir = Path(self.tmp_dir.name).joinpath("my_catalog")

        sys.argv = ["", "clone", input_path, "--target-dir", str(target_dir), "--name", "my_solution"]

        # run
        self.assertIsNone(main())

        # assert
        # FIXME this assertion fails because resolving the input path points to a different solution path in a temp download dir
        # self.assertIn(f"INFO - Copied solution {str(input_path)} to {self.tmp_dir.name}/my_catalog/my_solution/solution.py", self.captured_output.getvalue())
        self.assertTrue(target_dir.joinpath("my_solution", DefaultValues.solution_default_name.value).exists())

    def test_clone_solution_template(self):

        target_dir = Path(self.tmp_dir.name).joinpath("my_catalog")

        sys.argv = ["", "clone", "album:template-r:0.1.0-SNAPSHOT", "--target-dir", str(target_dir), "--name", "my_solution"]

        # run
        self.assertIsNone(main())

        # assert
        self.assertTrue(target_dir.joinpath("my_solution", DefaultValues.solution_default_name.value).exists())

    def test_clone_catalog_template(self):
        target_dir = Path(self.tmp_dir.name).joinpath("my_catalogs")

        sys.argv = ["", "clone", "catalog", "--target-dir", str(target_dir), "--name", "my_catalog"]

        # run
        self.assertIsNone(main())

        # assert
        target_path = Path(self.tmp_dir.name).joinpath("my_catalogs", "my_catalog")
        self.assertIn(f"INFO - Downloaded template from https://gitlab.com/album-app/catalogs/templates/catalog/-/archive/main/catalog-main.zip to {str(target_path)}", self.captured_output.getvalue())
        self.assertTrue(target_path.joinpath("album_catalog_index.json").exists())
        self.assertTrue(target_path.joinpath("album_solution_list.json").exists())

    def test_clone_non_existing_solution(self):
        sys.argv = ["", "clone", "weirdPath", "--target-dir", str(Path(self.tmp_dir.name)), "--name", "my_solution"]

        # run
        with self.assertRaises(LookupError):
            self.assertIsNone(main())


if __name__ == '__main__':
    unittest.main()

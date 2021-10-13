import sys
import unittest
from pathlib import Path

from album.argument_parsing import main
from album.core.model.default_values import DefaultValues
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationInstall(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_install_no_install_routine(self):
        # this solution has the no install() configured
        sys.argv = ["", "install", str(self.get_test_solution_path("solution0_dummy_no_routines.py"))]

        # run
        self.assertIsNone(main())

        # assert
        self.assertIn("No \"install\" routine configured for solution", self.captured_output.getvalue())

    def test_install(self):
        # gather arguments
        sys.argv = ["", "install", str(self.get_test_solution_path())]

        self.assertIsNone(main())

        # assert solution was added to local catalog
        collection = self.collection_manager.catalog_collection
        self.assertEqual(1, len(collection.get_solutions_by_catalog(self.collection_manager.catalogs().get_local_catalog().catalog_id)))

        # assert solution is in the right place and has the right name
        self.assertTrue(
            Path(self.tmp_dir.name).joinpath(
                DefaultValues.catalog_folder_prefix.value,
                str(self.collection_manager.catalogs().get_local_catalog().name),
                DefaultValues.cache_path_solution_prefix.value,
                "group", "name", "0.1.0", "solution.py"
            ).exists()
        )

    @unittest.skip("TODO this test fails on the Windows CI with \"SSL: CERTIFICATE_VERIFY_FAILED\" which might be related with the CI setup, not album itself")
    def test_install_from_url(self):
        # gather arguments
        sys.argv = ["", "install", "https://gitlab.com/album-app/catalogs/capture-knowledge-dev/-/raw/main/app-fiji/solution.py"]

        self.assertIsNone(main())

        # assert solution was added to local catalog
        collection = self.collection_manager.catalog_collection
        self.assertEqual(1, len(collection.get_solutions_by_catalog(self.collection_manager.catalogs().get_local_catalog().catalog_id)))

        # assert solution is in the right place and has the right name
        self.assertTrue(
            Path(self.tmp_dir.name).joinpath(
                DefaultValues.catalog_folder_prefix.value,
                str(self.collection_manager.catalogs().get_local_catalog().name),
                DefaultValues.cache_path_solution_prefix.value,
                "ida-mdc", "app-fiji", "0.1.0", "solution.py"
            ).exists()
        )

    def test_install_with_parent(self):
        # gather arguments
        sys.argv = ["", "install", str(self.get_test_solution_path("solution_with_parent_template.py"))]

        self.assertIsNone(main())

        # assert solution was added to local catalog
        collection = self.collection_manager.catalog_collection
        self.assertEqual(1, len(collection.get_solutions_by_catalog(
            self.collection_manager.catalogs().get_local_catalog().catalog_id)))

        # assert solution is in the right place and has the right name
        self.assertTrue(
            Path(self.tmp_dir.name).joinpath(
                DefaultValues.catalog_folder_prefix.value,
                str(self.collection_manager.catalogs().get_local_catalog().name),
                DefaultValues.cache_path_solution_prefix.value,
                "group", "solution_with_parent_template", "0_1_0", "solution.py"
            ).exists()
        )

    @unittest.skip("Needs to be implemented!")
    def test_install_with_dependencies(self):
        # ToDo: implement
        pass

    def test_install_no_solution(self):
        sys.argv = ["", "install"]
        with self.assertRaises(SystemExit) as e:
            main()
        self.assertEqual(SystemExit(2).code, e.exception.code)


if __name__ == '__main__':
    unittest.main()

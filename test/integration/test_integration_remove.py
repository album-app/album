import logging
import sys
import unittest
from unittest.mock import patch, PropertyMock

from hips.core.utils.operations.file_operations import create_path_recursively

from hips.argument_parsing import main
from hips.core.model.catalog_collection import HipsCatalogCollection
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationRemove(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    @patch('hips.core.controller.remove_manager.HipsCatalogCollection.resolve_from_str')
    @patch('hips.__main__.__retrieve_logger')
    def test_remove(self, logger_mock, res_from_str_mock):
        logger_mock.side_effect = [logging.getLogger("integration-test")]

        self.create_test_config()

        self.test_config_init += "- " + self.tmp_dir.name
        with open(self.closed_tmp_file.name, "w") as f:
            f.writelines(self.test_config_init)

        # resolving should return the relative path to the solution0_dummy resource file
        res_from_str_mock.return_value = {
            "path": self.get_test_solution_path("solution0_dummy_no_doi.py"),
            "catalog": self.test_catalog_collection.local_catalog
        }

        self.assertEqual(len(self.test_catalog_collection.local_catalog), 0)
        # manually add the solution0_dummy to the tmp-index
        self.test_catalog_collection.local_catalog.catalog_index.update({
            "group": "group",
            "name": "name",
            "version": "0.1.0",
        })
        self.assertEqual(len(self.test_catalog_collection.local_catalog), 1)

        # lets assume solution had downloads, caches and apps
        p = self.test_catalog_collection.configuration.cache_path_solution.joinpath(
            "local", "group", "name", "0.1.0", "a_cache_solution_file.txt"
        )
        create_path_recursively(p.parent)
        p.touch()

        p = self.test_catalog_collection.configuration.cache_path_download.joinpath(
            "local", "group", "name", "0.1.0", "a_cache_download_file.txt"
        )
        create_path_recursively(p.parent)
        p.touch()

        p = self.test_catalog_collection.configuration.cache_path_app.joinpath(
            "local", "group", "name", "0.1.0", "a_cache_app_file.txt"
        )
        create_path_recursively(p.parent)
        p.touch()

        sys.argv = ["", "remove", self.get_test_solution_path()]

        # overwrite the catalog_configuration attribute from the HipsRemover object to take our fake config
        with patch('hips.core.controller.remove_manager.RemoveManager.catalog_collection',
                   new_callable=PropertyMock) as p_mock:
            p_mock.return_value = self.test_catalog_collection
            self.assertIsNone(main())

        # assert that solution is removed from the catalog
        self.assertIn("Removed name", self.captured_output.getvalue())
        self.assertEqual(0, len(self.test_catalog_collection.local_catalog))

        # assert that the correct paths are deleted
        self.assertFalse(
            self.test_catalog_collection.configuration.cache_path_solution.joinpath(
                "local", "group", "name", "0.1.0"
            ).exists()
        )
        self.assertFalse(
            self.test_catalog_collection.configuration.cache_path_download.joinpath(
                "local", "group", "name", "0.1.0"
            ).exists()
        )
        self.assertFalse(
            self.test_catalog_collection.configuration.cache_path_app.joinpath(
                "local", "group", "name", "0.1.0"
            ).exists()
        )

    def test_remove_solution_not_installed(self):
        self.create_test_config()
        sys.argv = ["", "remove", self.get_test_solution_path()]

        with patch('hips.core.controller.remove_manager.RemoveManager.catalog_collection',
                   new_callable=PropertyMock) as p_mock:
            p_mock.return_value = self.test_catalog_collection
            with self.assertRaises(IndexError) as context:
                main()
                self.assertIn("WARNING - Solution points to a local file", str(context.exception))


if __name__ == '__main__':
    unittest.main()

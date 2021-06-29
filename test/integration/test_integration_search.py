import logging
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from hips.argument_parsing import main
from hips.core.model.catalog_collection import HipsCatalogCollection
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationSearch(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_search_no_keyword(self):
        sys.argv = ["", "search"]
        with self.assertRaises(SystemExit) as e:
            main()
        self.assertEqual(SystemExit(2).code, e.exception.code)

    def test_search_emtpy_index(self):
        sys.argv = ["", "search", "keyword"]
        self.assertIsNone(main())

    @patch('hips.core.controller.search_manager.HipsCatalogCollection.get_search_index')
    @patch('hips.__main__.__retrieve_logger')
    def test_search_filled_index(self, logger_mock, get_search_index_mock):
        # configure additional log output for checking
        logger_mock.side_effect = [logging.getLogger("integration-test")]

        self.test_config_init += "- " + str(Path(self.get_test_solution_path("")).joinpath("catalog_local"))
        with open(self.closed_tmp_file.name, mode="w") as f:
            f.writelines(self.test_config_init)

        # use config in test resources with relative path to a local catalog
        HipsCatalogCollection.instance = None  # lever out concept
        config = HipsCatalogCollection(self.closed_tmp_file.name)

        get_search_index_mock.return_value = {
            config.local_catalog.id: config.local_catalog.catalog_index.get_leaves_dict_list()
        }

        # define and run search
        sys.argv = ["", "search", "keyword1"]
        self.assertIsNone(main())

        # check output to have found the solution behind keyword1
        self.assertIn('catalog_local_ida-mdc_solution0_dummy_0.1.0', self.captured_output.getvalue())


if __name__ == '__main__':
    unittest.main()

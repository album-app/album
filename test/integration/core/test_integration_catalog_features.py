import sys
import unittest

from album.argument_parsing import main
from album.core.controller.catalog_manager import CatalogManager
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationCatalogFeatures(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_add_remove_catalog(self):
        catalog_configuration = CatalogManager()
        self.assertIsNotNone(catalog_configuration)
        initial_catalogs = catalog_configuration.config_file_dict["catalogs"].copy()
        self.assertIsNotNone(initial_catalogs)
        initial_len = len(initial_catalogs)
        somedir = "/tmp/somedir"
        sys.argv = ["", "add-catalog", somedir]
        self.assertIsNone(main())
        catalogs = CatalogManager().config_file_dict["catalogs"]
        self.assertEqual(initial_len + 1, len(catalogs))
        self.assertEqual(somedir, catalogs[len(catalogs) - 1])
        sys.argv = ["", "remove-catalog", somedir]
        self.assertIsNone(main())
        catalogs = CatalogManager().config_file_dict["catalogs"]
        self.assertEqual(initial_catalogs, catalogs)


if __name__ == '__main__':
    unittest.main()

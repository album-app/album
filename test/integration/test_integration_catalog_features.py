import sys
import unittest

from hips.argument_parsing import main
from hips.core.model.catalog_collection import HipsCatalogCollection
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationCatalogFeatures(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_search_no_keyword(self):
        sys.argv = ["", "search"]
        with self.assertRaises(SystemExit) as e:
            main()
        self.assertEqual(SystemExit(2).code, e.exception.code)

    def test_add_remove_catalog(self):
        catalog_configuration = HipsCatalogCollection()
        self.assertIsNotNone(catalog_configuration)
        initial_catalogs = catalog_configuration.config_file_dict["catalogs"]
        self.assertIsNotNone(initial_catalogs)
        initial_len = len(initial_catalogs)
        somedir = "/tmp/somedir"
        sys.argv = ["", "add-catalog", somedir]
        self.assertIsNone(main())
        catalogs = HipsCatalogCollection().config_file_dict["catalogs"]
        self.assertEqual(initial_len + 1, len(catalogs))
        self.assertEqual(somedir, catalogs[len(catalogs) - 1])
        sys.argv = ["", "remove-catalog", somedir]
        self.assertIsNone(main())
        catalogs = HipsCatalogCollection().config_file_dict["catalogs"]
        self.assertEqual(initial_catalogs, catalogs)


if __name__ == '__main__':
    unittest.main()

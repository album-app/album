import sys
import unittest
from pathlib import Path

from album.argument_parsing import main
from album.core.controller.catalog_manager import CatalogManager
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationCatalogFeatures(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def setUp(self):
        super().setUp()
        self.catalog_configuration = CatalogManager()

    def test_add_remove_catalog(self):
        # prepare
        self.assertIsNotNone(self.catalog_configuration)
        initial_catalogs = self.catalog_configuration.config_file_dict["catalogs"].copy()
        self.assertIsNotNone(initial_catalogs)
        initial_len = len(initial_catalogs)

        # gather arguments add
        somedir = str(Path(self.tmp_dir.name).joinpath("catalog_integration_test"))
        sys.argv = ["", "add-catalog", somedir]

        # call
        self.assertIsNone(main())

        # assert
        catalogs = CatalogManager().config_file_dict["catalogs"]
        self.assertEqual(initial_len + 1, len(catalogs))
        self.assertEqual(somedir, catalogs[len(catalogs) - 1])

        # gather arguments remove
        sys.argv = ["", "remove-catalog", somedir]

        # call
        self.assertIsNone(main())

        # assert
        catalogs = CatalogManager().config_file_dict["catalogs"]
        self.assertEqual(initial_catalogs, catalogs)


if __name__ == '__main__':
    unittest.main()

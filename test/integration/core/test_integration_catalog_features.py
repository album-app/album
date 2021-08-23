import sys
import unittest
from pathlib import Path

from album.argument_parsing import main
from album.core.controller.catalog_handler import CatalogHandler
from album.core.controller.collection_manager import CollectionManager
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationCatalogFeatures(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def setUp(self):
        super().setUp()
        self.catalog_configuration = CollectionManager().configuration

    def test_add_remove_catalog(self):
        # prepare
        self.assertIsNotNone(self.catalog_configuration)
        initial_catalogs = self.catalog_configuration.get_initial_catalogs().copy()
        self.assertIsNotNone(initial_catalogs)
        initial_len = len(initial_catalogs)

        # gather arguments add
        new_catalog = Path(self.tmp_dir.name).joinpath("catalog_integration_test")
        CatalogHandler.create_new_catalog(new_catalog, "catalog_integration_test")
        somedir = str(new_catalog)
        sys.argv = ["", "add-catalog", somedir]

        # call
        self.assertIsNone(main())

        # assert
        catalogs = CollectionManager().catalog_collection.get_all_catalogs()
        self.assertEqual(initial_len + 1, len(catalogs))
        self.assertEqual(somedir, catalogs[len(catalogs) - 1]["src"])

        # gather arguments remove
        sys.argv = ["", "remove-catalog", somedir]

        # call
        self.assertIsNone(main())

        # assert
        catalogs = CollectionManager().catalog_collection.get_all_catalogs()
        self.assertEqual(initial_len, len(catalogs))
        for catalog in catalogs:
            self.assertIsNotNone(initial_catalogs.get(catalog["name"], None))


if __name__ == '__main__':
    unittest.main()

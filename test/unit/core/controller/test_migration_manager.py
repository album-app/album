import shutil
import unittest
from unittest.mock import MagicMock

from album.core.model.catalog import Catalog
from album.core.model.default_values import DefaultValues
from test.unit.test_unit_core_common import TestCatalogAndCollectionCommon


class TestMigrationManager(TestCatalogAndCollectionCommon):

    def setUp(self):
        super().setUp()
        self.create_album_test_instance(init_catalogs=False)

        catalog_src_path = self.create_empty_catalog("testCat")
        self.catalog = Catalog(0, "test", src=catalog_src_path, path="catalog_path")

        self.migration_manager = self.album.migration_manager()
        self.migration_manager.load_index(self.catalog)

    def tearDown(self) -> None:
        self.catalog.dispose()
        super().tearDown()

    @unittest.skip("Needs to be implemented!")
    def test_migrate_or_create_collection(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_migrate_catalog_collection(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_migrate_catalog_locally(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_convert_catalog(self):
        pass

    def test_load_index(self):
        # prepare
        _load_catalog_index = MagicMock()
        self.migration_manager._load_catalog_index = _load_catalog_index

        set_version = MagicMock()
        self.album.catalogs().set_version = set_version

        update_index_cache = MagicMock()
        self.catalog.update_index_cache = update_index_cache

        # call
        self.migration_manager.load_index(self.catalog)

        # assert
        update_index_cache.assert_called_once()
        _load_catalog_index.assert_called_once()
        set_version.assert_called_once()

    @unittest.skip("Needs to be implemented!")
    def test_refresh_index(self):
        pass

    def test_refresh_index_broken_src(self):
        self.catalog = Catalog(1, "catalog_name", "catalog/path", "http://google.com/doesNotExist.ico")
        self.assertFalse(self.migration_manager.refresh_index(self.catalog))

    def test_validate_solution_attrs(self):
        self.create_test_solution_no_env()
        self.active_solution.setup().pop('timestamp')
        self.active_solution.setup().pop('album_version')
        self.migration_manager.validate_solution_attrs(self.active_solution.setup())

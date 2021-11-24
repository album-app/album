import shutil
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from album.core.controller.collection.catalog_handler import CatalogHandler
from album.core.controller.migration_manager import MigrationManager
from album.core.model.catalog import Catalog
from album.core.model.default_values import DefaultValues
from test.unit.test_unit_common import TestUnitCommon


class TestMigrationManager(TestUnitCommon):

    def setUp(self):
        super().setUp()
        self.create_album_test_instance(init_catalogs=False)

        # creates remote catalog file content
        catalog_src = Path(self.tmp_dir.name).joinpath("testRepo")
        CatalogHandler.create_new_catalog(catalog_src, "test")

        catalog_path = Path(self.tmp_dir.name).joinpath("testPath")
        catalog_path.mkdir(parents=True)

        # initiates new catalog
        self.catalog = Catalog(0, "test", src=catalog_src, path=catalog_path)
        MigrationManager().load_index(self.catalog)

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
        cs_file = Path(self.tmp_dir.name).joinpath(DefaultValues.catalog_index_file_name.value)
        shutil.copy(self.get_catalog_db_from_resources("minimal-solution"), cs_file)

        self.assertEqual(0, len(self.catalog.catalog_index))  # its the old catalog
        self.catalog.index_path = cs_file  # path to "new" catalog

        update_index_cache_mock = MagicMock()
        self.catalog.update_index_cache = update_index_cache_mock

        # call
        MigrationManager().load_index(self.catalog)

        # asssert
        self.assertEqual(1, len(self.catalog.catalog_index))  # now is the "new" catalog

    def test_refresh_index(self):
        cs_file = self.catalog.src.joinpath(DefaultValues.catalog_index_file_name.value)  # the catalog src db file
        shutil.copy(self.get_catalog_db_from_resources("empty"), cs_file)

        self.catalog.index_path = cs_file
        MigrationManager().refresh_index(self.catalog)
        self.assertEqual(0, len(self.catalog.catalog_index))

        shutil.copy(self.get_catalog_db_from_resources("minimal-solution"), cs_file)

        self.assertTrue(MigrationManager().refresh_index(self.catalog))
        self.assertTrue(1, len(self.catalog.catalog_index))

    def test_refresh_index_broken_src(self):
        self.catalog = Catalog(1, "catalog_name", "catalog/path", "http://google.com/doesNotExist.ico")
        self.assertFalse(MigrationManager().refresh_index(self.catalog))

    def test_validate_solution_attrs(self):
        self.create_test_solution_no_env()
        self.active_solution.setup.pop('timestamp')
        self.active_solution.setup.pop('album_version')
        MigrationManager().validate_solution_attrs(self.active_solution.setup)

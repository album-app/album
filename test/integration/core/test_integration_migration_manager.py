import os
import shutil
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

from album.core.model.catalog import Catalog
from album.core.model.db_version import DBVersion
from album.core.utils.operations.file_operations import get_dict_from_json
from test.integration.test_integration_core_common import TestIntegrationCoreCommon


class TestIntegrationMigrationManager(TestIntegrationCoreCommon):
    def setUp(self):
        super().setUp()
        self.setup_collection(init_catalogs=False)

        catalog_src_path, _ = self.setup_empty_catalog("testCat")
        self.catalog = Catalog(0, "test", src=catalog_src_path, path=self.tmp_dir.name)
        self.setup_outdated_temporary_collection()
        self.migration_manager = self.album_controller._migration_manager
        self.migration_manager.load_index(self.catalog)
        self.migration_manager.catalog_db_versions = [DBVersion.from_string('0.0.0'), DBVersion.from_string('0.0.1'),
                                                      DBVersion.from_string('0.1.0')]
        self.migration_manager.collection_db_versions = [DBVersion.from_string('0.0.0'), DBVersion.from_string('0.0.1'),
                                                         DBVersion.from_string('0.1.0')]
        self.collection_manager = self.album_controller._collection_manager

    def tearDown(self) -> None:
        self.catalog.dispose()
        super().tearDown()

    @staticmethod
    def check_migration(database, schema):
        conn = sqlite3.Connection(database)
        cursor = conn.cursor()
        cursor.execute(schema)
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return result

    def setup_outdated_temporary_collection(self):
        get_catalog_collection_meta_path = MagicMock()
        get_catalog_collection_meta_path.return_value = Path(self.tmp_dir.name).joinpath("catalog_collection.json")
        self.album_controller.configuration().get_catalog_collection_meta_path = get_catalog_collection_meta_path

        get_catalog_collection_path = MagicMock()
        get_catalog_collection_path.return_value = Path(self.tmp_dir.name).joinpath("catalog_collection.db")
        self.album_controller.configuration().get_catalog_collection_path = get_catalog_collection_path

        shutil.copyfile(Path(os.path.realpath(__file__)).parent.parent.parent.joinpath("resources",
                                                                                       "outdated_collection",
                                                                                       "catalog_collection.json"),
                        Path(self.tmp_dir.name).joinpath("catalog_collection.json"))
        shutil.copyfile(Path(os.path.realpath(__file__)).parent.parent.parent.joinpath("resources",
                                                                                       "outdated_collection",
                                                                                       "catalog_collection.db"),
                        Path(self.tmp_dir.name).joinpath("catalog_collection.db"))
        shutil.copyfile(Path(os.path.realpath(__file__)).parent.parent.parent.joinpath("resources", "catalogs", "unit",
                                                                                       "outdated_catalog",
                                                                                       "album_catalog_index.json"),
                        Path(self.tmp_dir.name).joinpath("album_catalog_index.json"))
        shutil.copyfile(Path(os.path.realpath(__file__)).parent.parent.parent.joinpath("resources", "catalogs", "unit",
                                                                                       "outdated_catalog",
                                                                                       "album_catalog_index.db"),
                        Path(self.tmp_dir.name).joinpath("album_catalog_index.db"))
        self.catalog.set_index_path(Path(self.tmp_dir.name).joinpath("album_catalog_index.db"))
        self.catalog._meta_file_path = Path(self.tmp_dir.name).joinpath("album_catalog_index.json")

    @patch('pkg_resources.resource_filename')
    def test_migrate_catalog_single(self, mock_resource_filename):
        # mocks
        mock_resource_filename.return_value = Path(os.path.realpath(__file__)).parent.parent.parent.joinpath(
            "resources",
            "migrations",
            "catalog_index",
            "migrate_catalog_index_001_to_010.sql")
        # prepare
        current_version = DBVersion.from_string("0.0.1")
        target_version = DBVersion.from_string("0.1.0")
        check_script = """SELECT name FROM sqlite_master WHERE type='table' AND name='test_table2';"""

        # call
        self.migration_manager._load_catalog_index(self.catalog, current_version)

        # prepare assert post call, needed since the assert needs to check the database which gets altered by the migration
        result = self.check_migration(self.catalog.index().get_path(), check_script)

        # assert
        self.assertEqual(str(target_version), self.catalog._version)
        self.assertEqual(str(target_version),
                         get_dict_from_json(
                             Path(self.tmp_dir.name).joinpath("album_catalog_index.json"))["version"])
        self.assertEqual("test_table2", result[0][0])
        self.catalog.__del__()  # close connection to db completely to avoid problems with the cleanup

    @patch('pkg_resources.resource_filename')
    def test_migrate_catalog_multiple(self, mock_resource_filename):
        # mocks
        mock_resource_filename.side_effect = [
            Path(os.path.realpath(__file__)).parent.parent.parent.joinpath("resources",
                                                                           "migrations",
                                                                           "catalog_index",
                                                                           "migrate_catalog_index_000_to_001.sql"),
            Path(os.path.realpath(__file__)).parent.parent.parent.joinpath(
                "resources",
                "migrations",
                "catalog_index",
                "migrate_catalog_index_001_to_010.sql")]
        # prepare
        current_version = DBVersion.from_string("0.0.0")
        target_version = DBVersion.from_string("0.1.0")
        check_script = """SELECT name FROM sqlite_master WHERE type='table' AND name='test_table2' OR name='test_table';"""

        # call
        self.migration_manager._load_catalog_index(self.catalog, current_version)

        # prepare assert post call, needed since the assert needs to check the database which gets altered by the migration
        result = self.check_migration(self.catalog.index().get_path(), check_script)

        # assert
        self.assertEqual(str(target_version), self.catalog._version)
        self.assertEqual(str(target_version),
                         get_dict_from_json(
                             Path(self.tmp_dir.name).joinpath("album_catalog_index.json"))["version"])
        self.assertEqual("test_table", result[0][0])
        self.assertEqual("test_table2", result[1][0])
        self.catalog.__del__()  # close connection to db completely to avoid problems with the cleanup

    @patch('pkg_resources.resource_filename')
    def test_migrate_catalog_collection_single(self, mock_resource_filename):
        # mocks
        mock_resource_filename.return_value = Path(os.path.realpath(__file__)).parent.parent.parent.joinpath(
            "resources",
            "migrations",
            "catalog_collection",
            "migrate_catalog_collection_001_to_010.sql")
        # prepare
        current_version = DBVersion.from_string("0.0.1")
        target_version = DBVersion.from_string("0.1.0")
        check_script = """SELECT name FROM sqlite_master WHERE type='table' AND name='test_table2';"""

        collection_path = MagicMock()
        collection_path.return_value = Path(self.tmp_dir.name).joinpath("catalog_collection.db")
        self.album_controller._collection_manager.catalog_collection.get_path = collection_path

        # call
        self.migration_manager.migrate_collection_index(self.album_controller._collection_manager.catalog_collection,
                                                        current_version)

        # prepare assert post call, needed since the assert needs to check the database which gets altered by the migration
        result = self.check_migration(Path(self.tmp_dir.name).joinpath("catalog_collection.db"), check_script)

        # assert
        self.assertEqual(str(target_version),
                         get_dict_from_json(
                             Path(self.tmp_dir.name).joinpath("catalog_collection.json"))["catalog_collection_version"])
        self.assertEqual("test_table2", result[0][0])

    @patch('pkg_resources.resource_filename')
    def test_migrate_catalog_collection_multiple(self, mock_resource_filename):
        # mock
        mock_resource_filename.side_effect = [
            Path(os.path.realpath(__file__)).parent.parent.parent.joinpath("resources",
                                                                           "migrations",
                                                                           "catalog_collection",
                                                                           "migrate_catalog_collection_000_to_001.sql"),
            Path(os.path.realpath(__file__)).parent.parent.parent.joinpath(
                "resources",
                "migrations",
                "catalog_collection",
                "migrate_catalog_collection_001_to_010.sql")]
        # prepare
        current_version = DBVersion.from_string("0.0.0")
        target_version = DBVersion.from_string("0.1.0")
        check_script = """SELECT name FROM sqlite_master WHERE type='table' AND name='test_table2' OR name='test_table';"""

        collection_path = MagicMock()
        collection_path.return_value = Path(self.tmp_dir.name).joinpath("catalog_collection.db")
        self.album_controller._collection_manager.catalog_collection.get_path = collection_path

        # call
        self.migration_manager.migrate_collection_index(
            self.album_controller._collection_manager.catalog_collection, current_version)

        # prepare assert post call, needed since the assert needs to check the database which gets altered by the migration
        result = self.check_migration(Path(self.tmp_dir.name).joinpath("catalog_collection.db"), check_script)

        # assert
        self.assertEqual(str(target_version),
                         get_dict_from_json(
                             Path(self.tmp_dir.name).joinpath("catalog_collection.json"))[
                             "catalog_collection_version"])
        self.assertEqual("test_table", result[0][0])
        self.assertEqual("test_table2", result[1][0])

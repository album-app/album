import json
import os.path
import shutil
import sqlite3
from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock, patch

from album.core.model.catalog import Catalog
from album.core.model.mmversion import MMVersion
from test.unit.test_unit_core_common import TestCatalogAndCollectionCommon


class TestMigrationManager(TestCatalogAndCollectionCommon):
    def setUp(self):
        super().setUp()
        self.setup_collection(init_catalogs=False)

        catalog_src_path, _ = self.setup_empty_catalog("testCat")
        self.catalog = Catalog(0, "test", src=catalog_src_path, path=self.tmp_dir.name)
        self.setup_outdated_temporary_collection()
        self.migration_manager = self.album_controller._migration_manager
        self.migration_manager.load_index(self.catalog)
        self.migration_manager.catalog_db_versions = [MMVersion.from_string('0.0.0'), MMVersion.from_string('0.0.1'),
                                                      MMVersion.from_string('0.1.0')]
        self.migration_manager.collection_db_versions = [MMVersion.from_string('0.0.0'), MMVersion.from_string('0.0.1'),
                                                         MMVersion.from_string('0.1.0')]

    def tearDown(self) -> None:
        self.catalog.dispose()
        super().tearDown()

    def setup_outdated_temporary_collection(self):
        get_catalog_collection_meta_path = MagicMock()
        get_catalog_collection_meta_path.return_value = Path(self.tmp_dir.name).joinpath("catalog_collection.json")
        self.album_controller.configuration().get_catalog_collection_meta_path = get_catalog_collection_meta_path

        get_catalog_collection_path = MagicMock()
        get_catalog_collection_path.return_value = Path(self.tmp_dir.name).joinpath("catalog_collection.db")
        self.album_controller.configuration().get_catalog_collection_path = get_catalog_collection_path

        shutil.copyfile(Path(os.path.realpath(__file__)).parent.parent.parent.parent.joinpath("resources",
                                                                                              "outdated_collection",
                                                                                              "catalog_collection.json"),
                        Path(self.tmp_dir.name).joinpath("catalog_collection.json"))
        shutil.copyfile(Path(os.path.realpath(__file__)).parent.parent.parent.parent.joinpath("resources",
                                                                                              "outdated_collection",
                                                                                              "catalog_collection.db"),
                        Path(self.tmp_dir.name).joinpath("catalog_collection.db"))

        shutil.copyfile(
            Path(os.path.realpath(__file__)).parent.parent.parent.parent.joinpath("resources", "catalogs", "unit",
                                                                                  "outdated_catalog",
                                                                                  "album_catalog_index.json"),
            Path(self.tmp_dir.name).joinpath("album_catalog_index.json"))
        shutil.copyfile(
            Path(os.path.realpath(__file__)).parent.parent.parent.parent.joinpath("resources", "catalogs", "unit",
                                                                                  "outdated_catalog",
                                                                                  "album_catalog_index.db"),
            Path(self.tmp_dir.name).joinpath("album_catalog_index.db"))

        self.catalog.set_index_path(Path(self.tmp_dir.name).joinpath("album_catalog_index.db"))
        self.catalog._meta_file_path = Path(self.tmp_dir.name).joinpath("album_catalog_index.json")

    def test_load_index(self):
        # prepare
        _load_catalog_index = MagicMock()
        self.migration_manager._load_catalog_index = _load_catalog_index

        set_version = MagicMock()
        self.album_controller.catalogs().set_version = set_version

        update_index_cache = MagicMock()
        self.catalog.update_index_cache = update_index_cache

        # call
        self.migration_manager.load_index(self.catalog)

        # assert
        update_index_cache.assert_called_once()
        _load_catalog_index.assert_called_once()
        set_version.assert_called_once()

    def test_refresh_index_broken_src(self):
        self.catalog = Catalog(
            1, "catalog_name", "catalog/path", "http://google.com/doesNotExist.ico"
        )
        self.assertFalse(self.migration_manager.refresh_index(self.catalog))

    def test_migrate_solution_attrs(self):
        self.setup_solution_no_env()
        self.active_solution.setup().pop("timestamp")
        self.active_solution.setup().pop("album_version")
        self.migration_manager.migrate_solution_attrs(self.active_solution.setup())

    def test_migrate_solution_schema0_attrs(self):
        self.setup_solution_no_env()
        self.active_solution.setup().pop("timestamp")
        self.active_solution.setup().pop("album_version")
        self.active_solution.setup()["album_api_version"] = "0.4.2"
        self.active_solution.setup()["authors"] = deepcopy(
            self.active_solution.setup()["solution_creators"]
        )
        self.active_solution.setup().pop("solution_creators")
        attrs = self.migration_manager.migrate_solution_attrs(
            self.active_solution.setup()
        )
        self.assertEqual(["a1", "a2"], attrs["solution_creators"])

    def test_migrate_collection_index(self):
        # prepare
        false_current_version = MMVersion.from_string("9.9.9")
        current_version = MMVersion.from_string("0.0.0")

        migrate_catalog_collection_db = MagicMock()
        self.migration_manager.migrate_catalog_collection_db = migrate_catalog_collection_db

        # call & assert
        with self.assertRaises(Exception):
            self.migration_manager.migrate_collection_index(
                self.album_controller._collection_manager.catalog_collection, false_current_version)

        self.migration_manager.migrate_collection_index(
            self.album_controller._collection_manager.catalog_collection, current_version)
        self.assertEqual(migrate_catalog_collection_db.call_count, 2)

    def test_load_catalog_index(self):
        # prepare
        current_version = MMVersion.from_string("0.0.0")
        false_current_version = MMVersion.from_string("9.9.9")

        migrate_catalog_index_db = MagicMock()
        self.migration_manager.migrate_catalog_index_db = migrate_catalog_index_db

        # call & assert
        with self.assertRaises(Exception):
            self.migration_manager._load_catalog_index(self.catalog, false_current_version)

        self.migration_manager._load_catalog_index(self.catalog, current_version)
        self.assertEqual(migrate_catalog_index_db.call_count, 2)

    def test_refresh_index(self):
        # prepare
        update_index_cache_if_possible = MagicMock()
        update_index_cache_if_possible.return_value = True
        self.catalog.update_index_cache_if_possible = update_index_cache_if_possible
        load_catalog_index = MagicMock()
        self.migration_manager._load_catalog_index = load_catalog_index

        # call
        self.migration_manager.refresh_index(self.catalog)

        # assert
        update_index_cache_if_possible.assert_called_once()
        load_catalog_index.assert_called_once()

    def test_load_solution_schema(self):
        pass

    @patch('pkg_resources.resource_filename')
    def test_load_catalog_collection_migration_schema(self, pkg_resources):
        # prepare
        pkg_resources.return_value = Path(os.path.realpath(__file__)).parent.parent.parent.parent.joinpath("resources", "migrations", "catalog_collection", "migrate_catalog_collection_001_to_010.sql")
        prep_schema = """CREATE TABLE IF NOT EXISTS test_table2 (
    spalte_1 INTEGER DEFAULT 0,
    spalte_2 TEXT DEFAULT "default"
);
UPDATE catalog_collection
SET version = '0.1.0'
WHERE name = 'album_collection'"""
        curr_version = MMVersion.from_string("0.0.1")
        target_version = MMVersion.from_string("0.1.0")

        # call
        called_schema = self.migration_manager._load_catalog_collection_migration_schema(curr_version, target_version)

        # assert
        self.assertEqual(prep_schema, called_schema)

    @patch('pkg_resources.resource_filename')
    def test_load_catalog_index_migration_schema(self, pkg_resources):
        # prepare
        pkg_resources.return_value = Path(os.path.realpath(__file__)).parent.parent.parent.parent.joinpath("resources", "migrations", "catalog_index", "migrate_catalog_index_001_to_010.sql")
        prep_schema = """CREATE TABLE IF NOT EXISTS test_table2 (
    spalte_1 INTEGER DEFAULT 0,
    spalte_2 TEXT DEFAULT "default"
);
UPDATE catalog_index
SET version = '0.1.0'
WHERE version = '0.0.1'"""
        curr_version = MMVersion.from_string("0.0.1")
        target_version = MMVersion.from_string("0.1.0")

        # call
        called_schema = self.migration_manager._load_catalog_index_migration_schema(curr_version, target_version)

        # assert
        self.assertEqual(prep_schema, called_schema)

    def test_execute_migration_script(self):
        # prepare
        check_script = """SELECT name FROM sqlite_master WHERE type='table' AND name='test_table';"""
        test_script = """CREATE TABLE IF NOT EXISTS test_table (
    spalte_1 INTEGER DEFAULT 0,
    spalte_2 TEXT DEFAULT "default"
);
UPDATE catalog_collection
SET version = '0.1.0'
WHERE name = 'album_collection'"""

        # call
        self.migration_manager._execute_migration_script(
            Path(self.tmp_dir.name).joinpath("catalog_collection.db"), test_script)

        # assert
        con = sqlite3.connect(Path(self.tmp_dir.name).joinpath("catalog_collection.db"))
        cur = con.cursor()
        self.assertTrue(cur.execute(check_script).fetchone()[0] == "test_table")
        cur.close()
        con.close()

    def test_update_catalog_collection_version(self):
        # call
        self.migration_manager._update_catalog_collection_version()

        # assert
        with open(Path(self.tmp_dir.name).joinpath("catalog_collection.json")) as file:
            self.assertTrue(json.load(file)["catalog_collection_version"] == "0.1.0")

    def test_update_catalog_index_version(self):
        # call
        self.migration_manager._update_catalog_index_version(
            Path(self.tmp_dir.name).joinpath("album_catalog_index.json"))

        # assert
        with open(Path(self.tmp_dir.name).joinpath("album_catalog_index.json")) as file:
            self.assertTrue(json.load(file)["version"] == "0.1.0")

    @patch("os.listdir")
    def test_read_collection_database_versions_from_scripts(self, listdir):
        # prepare
        listdir.return_value = ["migrate_catalog_collection_010_to_020.sql"]
        versions = [MMVersion.from_string("0.1.0"), MMVersion.from_string("0.2.0")]

        # call
        called_versions = self.migration_manager._read_collection_database_versions_from_scripts()

        # assert
        self.assertEqual(versions, called_versions)

    @patch("os.listdir")
    def test_read_catalog_database_versions_from_scripts(self, listdir):
        # prepare
        listdir.return_value = ["migrate_catalog_index_010_to_020.sql"]
        versions = [MMVersion.from_string("0.1.0"), MMVersion.from_string("0.2.0")]

        # call
        called_versions = self.migration_manager._read_catalog_database_versions_from_scripts()

        # assert
        self.assertEqual(versions, called_versions)

    @patch("os.listdir")
    def test_read_broken_collection_database_versions_from_scripts(self, listdir):
        # prepare
        listdir.return_value = ["migrate_catalog_collection_000_to_10.sql", "migrate_catalog_collection_010_to_020.sql"]

        # call & assert
        with self.assertRaises(ValueError):
            self.migration_manager._read_collection_database_versions_from_scripts()

    @patch("os.listdir")
    def test_read_broken_catalog_database_versions_from_scripts(self, listdir):
        # prepare
        listdir.return_value = ["migrate_catalog_index_000_to_01s.sql",
                                "migrate_catalog_index_010_to_020.sql"]
        # call & assert
        with self.assertRaises(ValueError):
            self.migration_manager._read_catalog_database_versions_from_scripts()

import json
import os
import pkgutil
import shutil
import sqlite3
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

import pkg_resources
from jsonschema import validate, ValidationError
from packaging import version

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.migration_manager import IMigrationManager
from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_index import ICollectionIndex
from album.core.model.db_version import IDBVersion, DBVersion
from album.runner import album_logging
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import write_dict_to_json, get_dict_from_json, get_dict_entry

module_logger = album_logging.get_active_logger


class MigrationManager(IMigrationManager):
    def __init__(self, album: IAlbumController):
        self.schema_solution = None
        self.schema_solution_runner_0_4_2 = None
        self.album = album
        self.collection_db_versions = self._read_collection_database_versions_from_scripts()
        self.catalog_db_versions = self._read_catalog_database_versions_from_scripts()

    def migrate_collection_index(self, collection_index: ICollectionIndex, initial_version: IDBVersion):
        current_version = initial_version
        target_version = DBVersion.from_string(DefaultValues.catalog_collection_db_version.value)
        if not current_version == target_version:
            if current_version < target_version:
                for vers in range(self.collection_db_versions.index(current_version),
                                  self.collection_db_versions.index(target_version)):
                    current_version = self.collection_db_versions[vers]
                    next_version = self.collection_db_versions[vers + 1]
                    self.migrate_catalog_collection_db(collection_index.get_path(), current_version, next_version)
            else:
                raise Exception("Your catalog collection database is newer than the current version of your Album. "
                                "Please Update your Album.")

    def _load_catalog_index(self, catalog: ICatalog, current_version: IDBVersion) -> None:
        """Loads current index on disk and migrates if necessary"""
        catalog.load_index()
        target_version = DBVersion.from_string(DefaultValues.catalog_index_db_version.value)
        if not current_version == target_version:
            if current_version < target_version:
                for vers in range(self.catalog_db_versions.index(current_version),
                                  self.catalog_db_versions.index(target_version)):
                    current_version = self.catalog_db_versions[vers]
                    next_version = self.catalog_db_versions[vers + 1]
                    self.migrate_catalog_index_db(catalog.index().get_path(), current_version, next_version)
            else:
                raise Exception("Your catalog index database of %s is newer than the current version of your Album. "
                                "Please Update your Album." % catalog.name())

    def migrate_catalog_collection_db(self, collection_index_path, curr_version, target_version):
        if not curr_version == target_version:
            if curr_version < target_version:
                module_logger().info("Migrating the collection database")
                with TemporaryDirectory(dir=self.album.configuration().tmp_path()) as tmp_dir:
                    # Save the database in case the migration fails and the database needs to be restored
                    shutil.copy(collection_index_path, Path(tmp_dir))
                    schema = self._load_catalog_collection_migration_schema(curr_version, target_version)
                    try:
                        self._execute_migration_script(collection_index_path, schema)
                        self._update_catalog_collection_version()
                    except Exception as e:
                        module_logger().error("Could not migrate the catalog collection database: %s" % e)
                        Path(collection_index_path).unlink()
                        shutil.copy(Path(tmp_dir).joinpath("catalog_collection.db"), collection_index_path)
            else:
                raise Exception("Your catalog collection database is newer than the current version of your Album. "
                                "Please Update your Album.")
        return collection_index_path

    def migrate_catalog_index_db(self, catalog_index_path, curr_version, target_version):
        if not curr_version == target_version:
            if curr_version < target_version:
                with TemporaryDirectory(dir=self.album.configuration().tmp_path()) as tmp_dir:
                    # Save the database in case the migration fails and the database needs to be restored
                    shutil.copy(catalog_index_path, Path(tmp_dir))
                    schema = self._load_catalog_index_migration_schema(curr_version, target_version)
                    try:
                        self._execute_migration_script(catalog_index_path, schema)
                        self._update_catalog_index_version(catalog_index_path)
                    except Exception as e:
                        module_logger().error("Could not migrate the catalog collection database: %s" % e)
                        Path(catalog_index_path).unlink()
                        shutil.copy(Path(tmp_dir).joinpath("album_catalog_index.db"), catalog_index_path)
            else:
                raise Exception("Your catalog index database is newer than the current version of your Album. "
                                "Please Update your Album.")
        return catalog_index_path

    def load_index(self, catalog: ICatalog):
        with TemporaryDirectory(dir=self.album.configuration().tmp_path()) as tmp_dir:
            catalog.update_index_cache(Path(tmp_dir))
            index_version = DBVersion.from_string(
                get_dict_entry(get_dict_from_json(catalog.get_meta_file_path()), 'version'))
        self._load_catalog_index(catalog, index_version)
        self.album.catalogs().set_version(catalog)

    def refresh_index(self, catalog: ICatalog) -> bool:
        with TemporaryDirectory(dir=self.album.configuration().tmp_path()) as tmp_dir:
            if catalog.update_index_cache_if_possible(tmp_dir):
                index_version = DBVersion.from_string(
                    get_dict_entry(get_dict_from_json(catalog.get_meta_file_path()), 'version'))
                self._load_catalog_index(catalog, index_version)
                return True
        return False

    def migrate_solution_attrs(self, attrs: dict) -> dict:
        self._load_solution_schema()
        if "album_api_version" not in attrs:
            raise ValidationError(
                "Your setup method is missing the 'album_api_version' keyword - the most recent "
                "version known to this album installation is '0.5.1'."
            )
        api_version = version.parse(attrs["album_api_version"])
        if api_version >= version.parse("0.5.1"):
            validate(attrs, self.schema_solution)
            return attrs
        else:
            validate(attrs, self.schema_solution_runner_0_4_2)
            return self._convert_schema0_schema1(attrs)

    def _load_solution_schema(self):
        if not self.schema_solution:
            data = pkgutil.get_data("album.runner.core.schema", "solution_schema.json")
            self.schema_solution = json.loads(data)
        if not self.schema_solution_runner_0_4_2:
            data = pkgutil.get_data("album.core.schema", "solution_schema_0.4.2.json")
            self.schema_solution_runner_0_4_2 = json.loads(data)

    @staticmethod
    def _load_catalog_collection_migration_schema(curr_version, target_version):
        with open(pkg_resources.resource_filename('album.core.schema.migrations.catalog_collection',
                                                  'migrate_catalog_collection_%s_to_%s.sql' % (
                                                          str(curr_version).replace('.', ''),
                                                          str(target_version).replace('.', '')))) as file:
            schema = file.read()
        return schema

    @staticmethod
    def _load_catalog_index_migration_schema(curr_version, target_version):
        with open(pkg_resources.resource_filename('album.core.schema.migrations.catalog_index',
                                                  'migrate_catalog_index_%s_to_%s.sql' % (
                                                          str(curr_version).replace('.', ''),
                                                          str(target_version).replace('.', '')))) as file:
            schema = file.read()
        return schema

    @staticmethod
    def _execute_migration_script(database, schema):
        connection = sqlite3.connect(database)
        cursor = connection.cursor()
        cursor.executescript(schema)
        connection.commit()
        connection.close()

    def _update_catalog_collection_version(self):
        catalog_collection_json_path = self.album.configuration().get_catalog_collection_meta_path()
        self.album.collection_manager().write_version_to_json(catalog_collection_json_path,
                                                              DefaultValues.catalog_collection_name.value,
                                                              DefaultValues.catalog_collection_db_version.value)

    @staticmethod
    def _update_catalog_index_version(catalog_index_path):
        catalog_index_json_path = Path(catalog_index_path).parent.joinpath(
            DefaultValues.catalog_index_metafile_json.value)
        index_dict = get_dict_from_json(catalog_index_json_path)
        index_dict["version"] = DefaultValues.catalog_index_db_version.value
        write_dict_to_json(catalog_index_json_path, index_dict)

    @staticmethod
    def _convert_schema0_schema1(attrs):
        if "authors" in attrs:
            attrs["solution_creators"] = deepcopy(attrs["authors"])
            attrs.pop("authors")
        return attrs

    @staticmethod
    def _read_collection_database_versions_from_scripts():
        versions = [DBVersion.from_string("0.1.0")]
        for file in os.listdir(pkg_resources.resource_filename('album.core.schema.migrations.catalog_collection', '')):
            if ".sql" in file:
                try:
                    versions.append(DBVersion.from_string(file.split("_")[-1].split(".")[0]))
                except (ValueError, IndexError):
                    raise ValueError("Could not parse version from file name: %s" % file)
        versions.sort()
        return versions

    @staticmethod
    def _read_catalog_database_versions_from_scripts():
        versions = [DBVersion.from_string("0.1.0")]
        for file in os.listdir(pkg_resources.resource_filename('album.core.schema.migrations.catalog_index', '')):
            if ".sql" in file:
                try:
                    versions.append(DBVersion.from_string(file.split("_")[-1].split(".")[0]))
                except (ValueError, IndexError):
                    raise ValueError("Could not parse version from file name: %s" % file)
        versions.sort()
        return versions

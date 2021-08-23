import os
from datetime import datetime
from pathlib import Path

from album.core.concept.database import Database
from album.core.model.album_base import AlbumClass
from album.core.model.configuration import Configuration
from album.core.model.default_values import DefaultValues
from album.core.model.group_name_version import GroupNameVersion
from album.core.utils.operations.file_operations import get_dict_entry, write_dict_to_json


class CollectionIndex(Database):
    version = "0.1.0"

    def __init__(self, name, path):
        self.name = name
        super().__init__(path)

    def create(self):
        current_path = Path(os.path.dirname(os.path.realpath(__file__)))
        with open(current_path.joinpath("..", "database", "catalog_collection_schema.sql")) as schema_file:
            schema = schema_file.read()
            self.get_cursor().executescript(schema)
        self.update_name_version(self.name, self.version)
        self.get_connection().commit()

    def update_name_version(self, name, version):
        curr_name = self.get_name()
        if curr_name:
            self.get_cursor().execute(
                "UPDATE catalog_collection SET name=:name, version=:version WHERE name_id=:name_id",
                {"name_id": 1, "name": name, "version": version}
            )
        else:
            self.get_cursor().execute(
                "INSERT INTO catalog_collection values (?, ?, ?)",
                (1, name, version)
            )

    def get_name(self):
        r = self.get_cursor().execute(
            "SELECT * FROM catalog_collection"
        ).fetchone()

        cur_name = r["name"] if r else None

        return cur_name

    def get_version(self):
        r = self.get_cursor().execute(
            "SELECT * FROM catalog_collection"
        ).fetchone()

        cur_version = r["version"] if r else None

        return cur_version

    def is_empty(self):
        r = self.get_cursor().execute("SELECT * FROM collection").fetchone()
        return False if r else True

    # ### catalog ###

    def insert_catalog(self, name, src, path, deletable):
        next_id = self.next_id("catalog")
        self.get_cursor().execute(
            "INSERT INTO catalog VALUES (?, ?, ?, ?, ?)",
            (
                next_id,
                name,
                src,
                path,
                deletable
            )
        )

        self.get_connection().commit()

        return next_id

    def get_catalog(self, catalog_id):
        r = self.get_cursor().execute(
            "SELECT * FROM catalog WHERE catalog_id=:catalog_id",
            {
                "catalog_id": catalog_id,
            }).fetchone()

        catalog = None
        if r:
            catalog = dict(r)

        return catalog

    def get_catalog_by_name(self, catalog_name):
        r = self.get_cursor().execute(
            "SELECT * FROM catalog WHERE name=:catalog_name",
            {
                "catalog_name": catalog_name,
            }).fetchone()

        catalog = None
        if r:
            catalog = dict(r)

        return catalog

    def get_catalog_by_path(self, catalog_path):
        r = self.get_cursor().execute(
            "SELECT * FROM catalog WHERE path=:catalog_path",
            {
                "catalog_path": catalog_path,
            }).fetchone()

        catalog = None
        if r:
            catalog = dict(r)

        return catalog

    def get_catalog_by_src(self, catalog_src):
        r = self.get_cursor().execute(
            "SELECT * FROM catalog WHERE src=:catalog_src",
            {
                "catalog_src": catalog_src,
            }).fetchone()

        catalog = None
        if r:
            catalog = dict(r)

        return catalog

    def get_all_catalogs(self):
        catalog_list = []
        cursor = self.get_cursor()
        for row in cursor.execute("SELECT * FROM catalog"):
            catalog_list.append(dict(row))

        return catalog_list

    def remove_catalog(self, catalog_id):
        self.get_cursor().execute(
            "DELETE FROM catalog WHERE catalog_id=:catalog_id",
            {
                "catalog_id": catalog_id,
            }
        )

    # ### collection ###

    def insert_solution(self, catalog_id, solution_attrs):
        next_id = self.next_id("collection")

        self.get_cursor().execute(
            "INSERT INTO collection VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? ,? ,?, ?, ? ,?, ?, ?, ?, ?)",
            (
                next_id,
                get_dict_entry(solution_attrs, "solution_id"),
                solution_attrs["group"],
                solution_attrs["name"],
                solution_attrs["title"],
                solution_attrs["version"],
                solution_attrs["format_version"],
                solution_attrs["timestamp"],
                solution_attrs["description"],
                get_dict_entry(solution_attrs, "doi"),  # allow to be none
                solution_attrs["git_repo"],
                solution_attrs["license"],
                solution_attrs["documentation"],
                solution_attrs["min_album_version"],
                solution_attrs["tested_album_version"],
                get_dict_entry(solution_attrs, "parent"),  # allow to be none
                get_dict_entry(solution_attrs, "changelog"),
                get_dict_entry(solution_attrs, "hash"),
                None,  # when installed?
                None,  # last executed
                0,  # installed
                catalog_id,
            )
        )

        self.get_connection().commit()

        return next_id

    def get_all_solutions(self):
        installed_solutions_list = []
        cursor = self.get_cursor()
        for row in cursor.execute("SELECT * FROM collection"):
            installed_solutions_list.append(dict(row))

        return installed_solutions_list

    def get_solutions_by_catalog(self, catalog_id):
        catalog_solutions = []
        cursor = self.get_cursor()
        for row in cursor.execute(
                "SELECT * FROM collection WHERE catalog_id=:catalog_id",
                {
                    "catalog_id": catalog_id
                }
        ):
            catalog_solutions.append(dict(row))

        return catalog_solutions

    def get_solution_by_hash(self, hash_value):
        r = self.get_cursor().execute(
            "SELECT * FROM collection WHERE hash=:hash_value",
            {
                "hash_value": hash_value
            }
        ).fetchone()

        solution = None
        if r:
            solution = dict(r)

        return solution

    def get_solution(self, collection_id):
        r = self.get_cursor().execute(
            "SELECT * FROM collection WHERE collection_id=:collection_id",
            {
                "collection_id": collection_id,
            }).fetchone()

        solution = None
        if r:
            solution = dict(r)

        return solution

    def get_solution_by_doi(self, doi):
        r = self.get_cursor().execute(
            "SELECT * FROM collection WHERE doi=:doi",
            {
                "doi": doi,
            }).fetchone()

        solution = None
        if r:
            solution = dict(r)

        return solution

    def get_solution_by_catalog_grp_name_version(self, catalog_id, group_name_version: GroupNameVersion):
        r = self.get_cursor().execute(
            "SELECT * FROM collection "
            "WHERE catalog_id=:catalog_id AND \"group\"=:group AND name=:name AND version=:version",
            {
                "catalog_id": catalog_id,
                "group": group_name_version.group,
                "name": group_name_version.name,
                "version": group_name_version.version,
            }
        ).fetchall()

        if len(r) > 1:
            raise KeyError("Database error. Please reinstall the solution %s from catalog %s !"
                           % (group_name_version.group, catalog_id))

        installed_solution = None
        for row in r:
            installed_solution = dict(row)

        return installed_solution

    def get_solutions_by_grp_name_version(self, group_name_version: GroupNameVersion):
        installed_solutions_list = []
        cursor = self.get_cursor()
        for row in cursor.execute(
                "SELECT * FROM collection WHERE \"group\"=:group AND name=:name AND version=:version",
                {
                    "group": group_name_version.group,
                    "name": group_name_version.name,
                    "version": group_name_version.version,
                }
        ):
            installed_solutions_list.append(dict(row))

        return installed_solutions_list

    def get_recently_installed_solutions(self):
        solutions_list = []
        cursor = self.get_cursor()
        for row in cursor.execute("SELECT * FROM collection ORDER BY install_date"):
            solutions_list.append(dict(row))
        return solutions_list

    def get_recently_launched_solutions(self):
        solutions_list = []
        cursor = self.get_cursor()
        for row in cursor.execute("SELECT * FROM collection WHERE last_execution IS NOT NULL ORDER BY last_execution"):
            solutions_list.append(dict(row))
        return solutions_list

    def update_solution(self, catalog_id, solution_attrs):
        exec_str = "UPDATE collection SET last_execution=:cur_date"
        exec_args = {
            "cur_date": datetime.now().isoformat(),
            "catalog_id": catalog_id,
            "group": solution_attrs["group"],
            "name": solution_attrs["name"],
            "version": solution_attrs["version"]
        }

        for key in self.get_solution_keys():
            if key in solution_attrs:
                col = self._as_db_col(key)
                exec_str += f", {col}=:{key}"
                exec_args[key] = get_dict_entry(solution_attrs, key)

        exec_str += " WHERE catalog_id=:catalog_id AND \"group\"=:group AND name=:name AND version=:version"

        self.get_cursor().execute(
            exec_str,
            exec_args
        )

        self.get_connection().commit()

    def get_solution_keys(self):
        keys = AlbumClass.deploy_keys.copy()
        keys.remove("authors")
        keys.remove("tags")
        keys.remove("args")
        keys.remove("cite")
        keys.remove("covers")
        keys.remove("sample_inputs")
        keys.remove("sample_outputs")
        keys.append("hash")
        keys.append("installed")
        return keys

    def add_or_replace_solution(self, catalog_id, group_name_version: GroupNameVersion, solution_attrs):
        solution = self.get_solution_by_catalog_grp_name_version(catalog_id, group_name_version)
        if solution:
            self.update_solution(catalog_id, solution_attrs)
        else:
            self.insert_solution(catalog_id, solution_attrs)

    def remove_solution(self, catalog_id, group_name_version: GroupNameVersion):
        self.get_cursor().execute(
            "DELETE FROM collection "
            "WHERE catalog_id=:catalog_id AND \"group\"=:group AND name=:name AND version=:version",
            {
                "catalog_id": catalog_id,
                "group": group_name_version.group,
                "name": group_name_version.name,
                "version": group_name_version.version,
            }
        )
        # TODO remove associated entries in other tables

    def insert_collection_tag(self, catalog_id, tag_id, tag_name, assignment_type, hash_val):
        if self.get_collection_tag_by_catalog_id_and_tag_id(catalog_id, tag_id, tag_name, assignment_type):
            return None

        collection_tag_id = self.next_id("collection_tag")
        self.get_cursor().execute(
            "INSERT INTO collection_tag values (?, ?, ?, ?, ?, ?)",
            (collection_tag_id, tag_id, catalog_id, tag_name, assignment_type, hash_val)
        )

        return tag_id

    # ### collection_tag ###

    def get_collection_tags_by_catalog_id(self, catalog_id):
        tag_list = []
        cursor = self.get_cursor()
        for row in cursor.execute(
                "SELECT * FROM collection_tag WHERE catalog_id=:catalog_id",
                {"catalog_id": catalog_id}
        ):
            tag_list.append(dict(row))
        return tag_list

    def get_collection_tag_by_catalog_id_and_name_and_type(self, catalog_id, tag_name, assignment_type):
        r = self.get_cursor().execute(
            "SELECT * FROM collection_tag WHERE "
            "catalog_id=:catalog_id AND name=:tag_name AND assignment_type=:assignment_type",
            {
                "catalog_id": catalog_id,
                "tag_name": tag_name,
                "assignment_type": assignment_type
            }).fetchone()

        return r

    def get_collection_tag_by_catalog_id_and_hash(self, catalog_id, tag_hash):
        r = self.get_cursor().execute(
            "SELECT * FROM collection_tag "
            "WHERE catalog_id=:catalog_id AND hash=:tag_hash ",
            {
                "catalog_id": catalog_id,
                "tag_id": tag_hash,
            }
        ).fetchone()

        if r:
            return dict(r)

        return None

    def get_collection_tag_by_catalog_id_and_tag_id(self, catalog_id, tag_id, tag_name, assignment_type):
        r = self.get_cursor().execute(
            "SELECT * FROM collection_tag "
            "WHERE catalog_id=:catalog_id AND tag_id=:tag_id "
            "AND name=:tag_name AND assignment_type=:assignment_type",
            {
                "catalog_id": catalog_id,
                "tag_id": tag_id,
                "tag_name": tag_name,
                "assignment_type": assignment_type
            }
        ).fetchone()

        if r:
            return dict(r)

        return None

    def insert_collection_solution_tag(self, catalog_id, solution_id, tag_id, hash_val):
        tag_ids = self.get_collection_solution_tags_by_catalog_id_and_solution_id(catalog_id, solution_id)

        if tag_id in tag_ids:
            return None

        solution_tag_id = self.next_id("collection_solution_tag")

        self.get_cursor().execute(
            "INSERT INTO collection_solution_tag values (?, ?, ?, ?)",
            (solution_tag_id, solution_id, tag_id, hash_val)
        )

        return solution_tag_id

    # ### collection_solution_tag ###

    def get_collection_solution_tags_by_catalog_id_and_solution_id(self, catalog_id, solution_id):
        tag_ids = []
        r = self.get_cursor().execute(
            "SELECT * FROM collection_solution_tag WHERE catalog_id=:catalog_id AND solution_id=:solution_id",
            {
                "catalog_id": catalog_id,
                "solution_id": solution_id,
            }).fetchall()

        for row in r:
            tag_ids.append(row["tag_id"])

        return tag_ids

    def get_collection_solution_tag_by_catalog_id_and_hash(self, catalog_id, hash_value):
        r = self.get_cursor().execute(
            "SELECT * FROM collection_solution_tag "
            "WHERE catalog_id=:catalog_id AND hash=:hash_value",
            {
                "catalog_id": catalog_id,
                "hash_value": hash_value
            }
        ).fetchone()

        if r:
            return dict(r)

        return None

    def get_collection_solution_tags_by_catalog_id(self, catalog_id):
        solution_tag_list = []
        cursor = self.get_cursor()
        for row in cursor.execute(
                "SELECT * FROM collection_solution_tag WHERE catalog_id=:catalog_id",
                {
                    "catalog_id": catalog_id
                }
        ):
            solution_tag_list.append(dict(row))
        return solution_tag_list

    def get_collection_solution_tag_by_catalog_id_and_solution_id_and_tag_id(self, catalog_id, solution_id, tag_id):
        r = self.get_cursor().execute(
            "SELECT * FROM collection_solution_tag "
            "WHERE catalog_id=:catalog_id AND solution_id=:solution_id AND tag_id=:tag_id",
            {
                "catalog_id": catalog_id,
                "solution_id": solution_id,
                "tag_id": tag_id
            }
        ).fetchone()

        if r:
            return dict(r)

        return None

    def is_installed(self, catalog_id, group_name_version: GroupNameVersion):
        r = self.get_solution_by_catalog_grp_name_version(catalog_id, group_name_version)
        if not r:
            raise LookupError(f"Solution {catalog_id}:{group_name_version} not found!")
        return True if r["installed"] else False

    # ### catalog_collection features ###

    def remove_entire_catalog(self, catalog_id):
        self.get_cursor().execute(
            "DELETE FROM collection "
            "WHERE catalog_id=:catalog_id",
            {
                "catalog_id": catalog_id
            }
        )
        self.get_cursor().execute(
            "DELETE FROM collection_solution_tag "
            "WHERE catalog_id=:catalog_id",
            {
                "catalog_id": catalog_id
            }
        )
        self.get_cursor().execute(
            "DELETE FROM collection_tag "
            "WHERE catalog_id=:catalog_id",
            {
                "catalog_id": catalog_id
            }
        )
        self.get_cursor().execute(
            "DELETE FROM catalog "
            "WHERE catalog_id=:catalog_id",
            {
                "catalog_id": catalog_id
            }
        )

    def __len__(self):
        r = self.get_cursor().execute("SELECT COUNT(*) FROM collection").fetchone()
        r = r[0]

        return r

    @staticmethod
    def write_version_to_yml(name, version):
        d = {
            "catalog_collection_name": name,
            "catalog_collection_version": version
        }
        write_dict_to_json(
            Path(Configuration().catalog_collection_path).joinpath(DefaultValues.catalog_collection_json_name.value),
            d
        )

    @staticmethod
    def _as_db_col(key):
        if key is "group":
            return "\"group\""
        return key

import datetime
import hashlib
import json
import os
from pathlib import Path

from album.core import AlbumClass
from album.core.concept.database import Database
from album.core.utils.operations.file_operations import get_dict_entry, write_dict_to_json


class CatalogIndex(Database):
    """Class handling the index of all solutions in a catalog."""

    version = "0.1.0"

    def __init__(self, name, path):
        """Init routine.

        Args:
            name:
                The name of the catalog.
            path:
                The path to the index file.

        """
        self.name = name
        super().__init__(path)

    def create(self):
        current_path = Path(os.path.dirname(os.path.realpath(__file__)))
        with open(current_path.joinpath("..", "database", "catalog_index_schema.sql")) as schema_file:
            schema = schema_file.read()
            self.get_cursor().executescript(schema)

        self.update_name_version(self.name, self.version)
        self.get_connection().commit()

    def is_empty(self):
        r = self.get_cursor().execute("SELECT * FROM solution").fetchone()
        return False if r else True

    def is_table_empty(self, table):
        r = self.get_cursor().execute("SELECT * FROM %s" % table).fetchone()
        return False if r else True

    # ### catalog_index ###

    def update_name_version(self, name, version):
        curr_name = self.get_name()
        if curr_name:
            self.get_cursor().execute(
                "UPDATE catalog_index SET name=:name, version=:version WHERE name_id=:name_id",
                {"name_id": 1, "name": name, "version": version}
            )
        else:
            self.get_cursor().execute(
                "INSERT INTO catalog_index values (?, ?, ?)",
                (1, name, version)
            )

    def get_name(self):
        r = self.get_cursor().execute(
            "SELECT * FROM catalog_index"
        ).fetchone()

        cur_name = r["name"] if r else None

        return cur_name

    def get_version(self):
        r = self.get_cursor().execute(
            "SELECT * FROM catalog_index"
        ).fetchone()

        cur_version = r["version"] if r else None

        return cur_version

    # ### tag ###

    def insert_tag(self, tag_name, assignment_type):
        if self.get_tag_by_name_and_type(tag_name, assignment_type):
            return None

        hash_val = hashlib.md5(":".join([tag_name, assignment_type]).encode('utf-8')).hexdigest()

        tag_id = self.next_id("tag")
        self.get_cursor().execute(
            "INSERT INTO tag values (?, ?, ?, ?)",
            (tag_id, tag_name, assignment_type, hash_val)
        )

        return tag_id

    def get_tag(self, tag_id):
        r = self.get_cursor().execute(
            "SELECT * FROM tag WHERE tag_id=:tag_id",
            {
                "tag_id": tag_id,
            }).fetchone()
        tag = None
        if r:
            tag = dict(r)
        return tag

    def get_tag_by_hash(self, tag_hash):
        r = self.get_cursor().execute(
            "SELECT * FROM tag WHERE hash=:tag_hash",
            {
                "tag_hash": tag_hash,
            }).fetchone()
        tag = None
        if r:
            tag = dict(r)
        return tag

    def get_tags_by_name(self, tag_name):
        r = self.get_cursor().execute(
            "SELECT * FROM tag WHERE name=:tag_name",
            {
                "tag_name": tag_name,
            }).fetchall()
        tags = []
        for _r in r:
            tags.append(dict(_r))
        return tags

    def get_tag_by_name_and_type(self, tag_name, assignment_type):
        r = self.get_cursor().execute(
            "SELECT * FROM tag WHERE name=:tag_name AND assignment_type=:assignment_type",
            {
                "tag_name": tag_name,
                "assignment_type": assignment_type
            }).fetchone()

        tag = None
        if r:
            tag = dict(r)
        return tag

    def remove_tag(self, tag_id):
        self.get_cursor().execute(
            "DELETE FROM tag WHERE tag_id=:tag_id",
            {
                "tag_id": tag_id
            }
        )

    def remove_tag_by_name(self, tag_name):
        self.get_cursor().execute(
            "DELETE FROM tag WHERE name=:tag_name",
            {
                "tag_name": tag_name
            }
        )

    def remove_tag_by_name_and_type(self, tag_name, assignment_type):
        self.get_cursor().execute(
            "DELETE FROM tag WHERE name=:tag_name AND assignment_type=:assignment_type",
            {
                "tag_name": tag_name,
                "assignment_type": assignment_type
            }
        )

    # ### solution_tag ###

    def insert_solution_tag(self, solution_id, tag_id):
        tag_ids = self.get_solution_tags(solution_id)

        if tag_id in tag_ids:
            return None

        hash_val = self.create_hash(":".join([json.dumps(solution_id), json.dumps(tag_id)]))

        solution_tag_id = self.next_id("solution_tag")

        self.get_cursor().execute(
            "INSERT INTO solution_tag values (?, ?, ?, ?)",
            (solution_tag_id, solution_id, tag_id, hash_val)
        )

        return solution_tag_id

    def get_all_solutions(self):
        r = self.get_cursor().execute(
            "SELECT * FROM solution",
            {})

        solutions = []
        if r:
            for s in r:
                solutions.append(dict(s))
        return solutions

    def get_solution_tag_by_hash(self, hash_value):
        r = self.get_cursor().execute(
            "SELECT * FROM solution_tag WHERE hash=:hash_value",
            {
                "hash_value": hash_value,
            }).fetchone()

        solution_tag = None
        if r:
            solution_tag = dict(r)
        return solution_tag

    def get_solution_tag_by_solution_id_and_tag_id(self, solution_id, tag_id):
        r = self.get_cursor().execute(
            "SELECT * FROM solution_tag WHERE solution_id=:solution_id AND tag_id=:tag_id",
            {
                "solution_id": solution_id,
                "tag_id": tag_id
            }).fetchone()
        solution_tag = None
        if r:
            solution_tag = dict(r)
        return solution_tag

    def get_solution_tags(self, solution_id):
        tag_ids = []
        r = self.get_cursor().execute(
            "SELECT * FROM solution_tag WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id,
            }).fetchall()

        for row in r:
            tag_ids.append(row["tag_id"])

        return tag_ids

    def remove_solution_tags(self, solution_id):
        self.get_cursor().execute(
            "DELETE FROM solution_tag WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        )

    # ### solution ###

    def _insert_solution(self, solution_attrs):
        hash_val = self.create_hash(":".join([json.dumps(solution_attrs[k]) for k in solution_attrs.keys()]))
        solution_id = self.next_id("solution")
        self.get_cursor().execute(
            "INSERT INTO solution values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? ,? ,?, ?, ?)",
            (
                solution_id,
                solution_attrs["group"],
                solution_attrs["name"],
                solution_attrs["title"],
                solution_attrs["version"],
                solution_attrs["format_version"],
                datetime.datetime.now().isoformat(),
                solution_attrs["description"],
                get_dict_entry(solution_attrs, "doi"),  # allow to be none
                solution_attrs["git_repo"],
                solution_attrs["license"],
                solution_attrs["documentation"],
                solution_attrs["min_album_version"],
                solution_attrs["tested_album_version"],
                get_dict_entry(solution_attrs, "parent"),  # allow to be none
                get_dict_entry(solution_attrs, "changelog"),  # allow to be none
                hash_val
            )
        )
        return solution_id

    def get_solution(self, solution_id):
        r = self.get_cursor().execute(
            "SELECT * FROM solution WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id,
            }).fetchone()
        solution = None
        if r:
            solution = dict(r)
        return solution

    def get_solution_by_group_name_version(self, group, name, version):
        """Resolves a solution by its name, version and group.

        Args:
            group:
                The group affiliation of the solution.
            name:
                The name of the solution.
            version:
                The version of the solution.

        Returns:
            None or row not found.

        """
        cursor = self.get_cursor()

        r = cursor.execute(
            "SELECT * FROM solution WHERE \"group\"=:group AND name=:name AND version=:version",
            {
                "group": group,
                "name": name,
                "version": version,
            }
        ).fetchone()

        solution = None
        if r:
            solution = dict(r)
        return solution

    def get_solution_by_doi(self, doi):
        """Resolves a solution by its DOI.

        Args:
            doi:
                The doi to resolve for.

        Returns:
            None or a node if any found.

        Raises:
            RuntimeError if the DOI was found more than once.
                         if the node found is not a leaf

        """
        cursor = self.get_cursor()

        r = cursor.execute(
            "SELECT * FROM solution WHERE doi=:doi_value",
            {
                "doi_value": doi,
            }
        ).fetchone()

        solution = None
        if r:
            solution = dict(r)
        return solution

    def _update_solution(self, solution_attrs):
        hash_val = self.create_hash(":".join([json.dumps(solution_attrs[k]) for k in solution_attrs.keys()]))

        self.get_cursor().execute(
            "UPDATE solution SET "
            "title=:title, "
            "format_version=:format_version, "
            "timestamp=:timestamp, "
            "description=:description, "
            "doi=:doi, "
            "git_repo=:git_repo, "
            "license=:license, "
            "documentation=:documentation, "
            "min_album_version=:min_album_version, "
            "tested_album_version=:tested_album_version, "
            "parent=:parent, "
            "changelog=:changelog,"
            "hash=:hash_val "
            "WHERE \"group\"=:group AND name=:name AND version=:version",
            {
                "group": solution_attrs["group"],
                "name": solution_attrs["name"],
                "version": solution_attrs["version"],
                "title": solution_attrs["title"],
                "format_version": solution_attrs["format_version"],
                "timestamp": "",
                "description": solution_attrs["description"],
                "doi": get_dict_entry(solution_attrs, "doi"),
                "git_repo": solution_attrs["git_repo"],
                "license": solution_attrs["license"],
                "documentation": solution_attrs["documentation"],
                "min_album_version": solution_attrs["min_album_version"],
                "tested_album_version": solution_attrs["tested_album_version"],
                "parent": get_dict_entry(solution_attrs, "parent"),
                "changelog": get_dict_entry(solution_attrs, "changelog"),
                "hash_val": hash_val
            }
        )

    def remove_solution(self, solution_id):
        # delete tags first
        self.remove_solution_tags(solution_id)

        # delete solution afterwards
        self.get_cursor().execute(
            "DELETE FROM solution WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        )

    def remove_solution_by_group_name_version(self, group, name, version):
        solution_dict = self.get_solution_by_group_name_version(group, name, version)
        if solution_dict:
            self.remove_solution(solution_dict["solution_id"])

    # ### catalog_features ###

    def insert(self, active_solution: AlbumClass):
        solution_attrs = active_solution.get_deploy_dict()

        # insert tags if not already present
        # insert solution
        # insert solution-tag connection
        # return solution id
        return 1

    def remove(self, active_solution: AlbumClass):
        solution_attrs = active_solution.get_deploy_dict()

        # remove solution-tag connection
        # remove solution

    def update(self, solution_attrs: dict):
        """Updates a catalog to include a solution as a node with the attributes given.
         Updates exiting nodes if node already present in tree.

        Args:
            solution_attrs:
                The solution attributes. Must hold group, name, version.

        """
        group, name, version = self.check_requirements(solution_attrs)

        # insert tags
        for tag in solution_attrs["tags"]:
            self.insert_tag(tag, "manual")

        if self.get_solution_by_group_name_version(group, name, version):
            self._update_solution(solution_attrs)
        else:
            self._insert_solution(solution_attrs)

    def save(self):
        self.get_connection().commit()

    def export(self, path, export_format="JSON"):
        """Exports the index tree to disk.

        Args:
            path:
                The path to store the export to.
            export_format:
                The format to save to. Choose from ["JSON"]. (Default: JSON)

        Raises:
            NotImplementedError if the format is not supported.

        """
        r = self.get_cursor().execute("SELECT * FROM solution").fetchall()

        if export_format == "JSON":
            json_dumps_list = []
            for solution in r:
                solution = dict(solution)
                solution["tags"] = self.get_solution_tags(solution["solution_id"])
                json_dumps_list.append(json.dumps(solution))

            write_dict_to_json(path, json_dumps_list)
        else:
            raise NotImplementedError("Unsupported format \"%s\"" % export_format)

    @staticmethod
    def check_requirements(solution_attrs):
        for key in AlbumClass.deploy_keys:
            get_dict_entry(solution_attrs, key, allow_none=False, message="Key %s in solution not set!" % key)

        group = solution_attrs["group"]
        name = solution_attrs["name"]
        version = solution_attrs["version"]

        return group, name, version

    def __len__(self):
        r = self.get_cursor().execute("SELECT COUNT(*) FROM solution").fetchone()
        r = r[0]

        return r

    @staticmethod
    def create_hash(string_representation):
        hash_val = hashlib.md5(string_representation.encode('utf-8')).hexdigest()

        return hash_val

import json
import pkgutil
from datetime import datetime
from typing import Optional

from album.core.concept.database import Database
from album.core.model.catalog_index import CatalogIndex
from album.core.model.coordinates import Coordinates
from album.core.utils.operations.file_operations import get_dict_entry


class CollectionIndex(Database):
    version = "0.1.0"

    def __init__(self, name, path):
        self.name = name
        super().__init__(path)

    def create(self):
        data = pkgutil.get_data('album.core.database', 'catalog_collection_schema.sql')
        cursor = self.get_cursor()
        cursor.executescript(data.decode("utf-8"))
        self.update_name_version(self.name, self.version, close=False)

        self.close_current_connection()

    def update_name_version(self, name, version, close=True):
        curr_name = self.get_name(close=False)

        cursor = self.get_cursor()
        if curr_name:
            cursor.execute(
                "UPDATE catalog_collection SET name=:name, version=:version WHERE name_id=:name_id",
                {"name_id": 1, "name": name, "version": version}
            )
        else:
            cursor.execute(
                "INSERT INTO catalog_collection values (?, ?, ?)",
                (1, name, version)
            )

        if close:
            self.close_current_connection()

    def get_name(self, close=True):
        cursor = self.get_cursor()

        r = cursor.execute(
            "SELECT * FROM catalog_collection"
        ).fetchone()

        cur_name = r["name"] if r else None

        if close:
            self.close_current_connection()

        return cur_name

    def get_version(self, close=True):
        cursor = self.get_cursor()

        r = cursor.execute(
            "SELECT * FROM catalog_collection"
        ).fetchone()

        cur_version = r["version"] if r else None

        if close:
            self.close_current_connection()

        return cur_version

    def is_empty(self, close=True):
        cursor = self.get_cursor()

        r = cursor.execute("SELECT * FROM collection").fetchone()

        if close:
            self.close_current_connection()

        return False if r else True

    # ### catalog ###

    def insert_catalog(self, name, src, path, deletable, close=True):
        next_id = self.next_id("catalog")
        cursor = self.get_cursor()

        cursor.execute(
            "INSERT INTO catalog VALUES (?, ?, ?, ?, ?)",
            (
                next_id,
                name,
                src,
                path,
                deletable
            )
        )

        if close:
            self.close_current_connection()

        return next_id

    def get_catalog(self, catalog_id, close=True):
        cursor = self.get_cursor()

        r = cursor.execute(
            "SELECT * FROM catalog WHERE catalog_id=:catalog_id",
            {
                "catalog_id": catalog_id,
            }).fetchone()

        catalog = None
        if r:
            catalog = dict(r)

        if close:
            self.close_current_connection()

        return catalog

    def get_catalog_by_name(self, catalog_name, close=True):
        cursor = self.get_cursor()

        r = cursor.execute(
            "SELECT * FROM catalog WHERE name=:catalog_name",
            {
                "catalog_name": catalog_name,
            }).fetchone()

        catalog = None
        if r:
            catalog = dict(r)

        if close:
            self.close_current_connection()

        return catalog

    def get_catalog_by_path(self, catalog_path, close=True):
        cursor = self.get_cursor()

        r = cursor.execute(
            "SELECT * FROM catalog WHERE path=:catalog_path",
            {
                "catalog_path": catalog_path,
            }).fetchone()

        catalog = None
        if r:
            catalog = dict(r)

        if close:
            self.close_current_connection()

        return catalog

    def get_catalog_by_src(self, catalog_src, close=True):
        cursor = self.get_cursor()

        r = cursor.execute(
            "SELECT * FROM catalog WHERE src=:catalog_src",
            {
                "catalog_src": catalog_src,
            }).fetchone()

        catalog = None
        if r:
            catalog = dict(r)

        if close:
            self.close_current_connection()

        return catalog

    def get_all_catalogs(self, close=True):
        catalog_list = []
        cursor = self.get_cursor()
        for row in cursor.execute("SELECT * FROM catalog"):
            catalog_list.append(dict(row))

        if close:
            self.close_current_connection()

        return catalog_list

    # ### collection ###

    def insert_solution(self, catalog_id, solution_attrs, close=True):
        next_id = self.next_id("collection")
        hash_val = get_dict_entry(solution_attrs, "hash", allow_none=True)

        # there must be a hash value
        if not hash_val:
            hash_val = CatalogIndex.create_hash(
                ":".join([json.dumps(solution_attrs[k]) for k in solution_attrs.keys()])
            )

        cursor = self.get_cursor()
        cursor.execute(
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
                hash_val,
                None,  # when installed?
                None,  # last executed
                0,  # installed
                catalog_id,
            )
        )

        for author in solution_attrs["authors"]:
            # fixme: what if author already in DB?
            author_id = self._insert_author(author, catalog_id, close=False)
            collection_solution_author_id = self.next_id("collection_solution_author")
            cursor.execute(
                "INSERT INTO collection_solution_author values (?, ?, ?, ?)",
                (
                    collection_solution_author_id,
                    next_id,
                    author_id,
                    catalog_id
                )
            )

        for tag in solution_attrs["tags"]:
            # fixme: what if author already in DB?
            tag_id = self._insert_tag(tag, catalog_id, close=False)
            collection_solution_tag_id = self.next_id("collection_solution_tag")
            cursor.execute(
                "INSERT INTO collection_solution_tag values (?, ?, ?, ?)",
                (
                    collection_solution_tag_id,
                    next_id,
                    tag_id,
                    catalog_id
                )
            )

        for citation in solution_attrs["cite"]:
            # fixme: what if author already in DB?
            citation_id = self._insert_citation(citation, catalog_id, close=False)
            collection_solution_citation_id = self.next_id("collection_solution_citation")
            cursor.execute(
                "INSERT INTO collection_solution_citation values (?, ?, ?, ?)",
                (
                    collection_solution_citation_id,
                    next_id,
                    citation_id,
                    catalog_id
                )
            )

        for argument in solution_attrs["args"]:
            # fixme: what if author already in DB?
            argument_id = self._insert_argument(argument, catalog_id, close=False)
            collection_solution_argument_id = self.next_id("collection_solution_argument")
            cursor.execute(
                "INSERT INTO collection_solution_argument values (?, ?, ?, ?)",
                (
                    collection_solution_argument_id,
                    next_id,
                    argument_id,
                    catalog_id
                )
            )

        for cover in solution_attrs["covers"]:
            self._insert_cover(cover, catalog_id, next_id)

        if close:
            self.close_current_connection()

        return next_id

    def _insert_author(self, author, catalog_id, close=True):
        author_id = self.next_id("collection_author")

        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO collection_author values (?, ?, ?)",
            (
                author_id,
                catalog_id,
                author
            )
        )

        if close:
            self.close_current_connection()

        return author_id

    def _insert_tag(self, tag, catalog_id, close=True):
        tag_id = self.next_id("collection_tag")
        cursor = self.get_cursor()

        cursor.execute(
            "INSERT INTO collection_tag values (?, ?, ?, ?)",
            (
                tag_id,
                catalog_id,
                tag,
                "manual"
            )
        )

        if close:
            self.close_current_connection()

        return tag_id

    def _insert_argument(self, argument, catalog_id, close=True):
        argument_id = self.next_id("collection_argument")
        cursor = self.get_cursor()

        cursor.execute(
            "INSERT INTO collection_argument values (?, ?, ?, ?, ?, ?)",
            (
                argument_id,
                catalog_id,
                argument["name"],
                get_dict_entry(argument, "type"),
                argument["description"],
                get_dict_entry(argument, "default_value")
            )
        )

        if close:
            self.close_current_connection()

        return argument_id

    def _insert_citation(self, citation, catalog_id, close=True):
        citation_id = self.next_id("collection_citation")

        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO collection_citation values (?, ?, ?, ?)",
            (
                citation_id,
                catalog_id,
                citation["text"],
                get_dict_entry(citation, "doi")
            )
        )

        if close:
            self.close_current_connection()

        return citation_id

    def _insert_cover(self, cover, catalog_id, collection_id, close=True):
        cover_id = self.next_id("collection_cover")

        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO collection_cover values (?, ?, ?, ?, ?)",
            (
                cover_id,
                collection_id,
                catalog_id,
                cover["source"],
                cover["description"]
            )
        )

        if close:
            self.close_current_connection()

        return cover_id

    def get_all_solutions(self, close=True):
        installed_solutions_list = []
        cursor = self.get_cursor()
        for row in cursor.execute("SELECT * FROM collection").fetchall():
            solution_dict = dict(row)
            self._append_metadata_to_solution(solution_dict)
            installed_solutions_list.append(solution_dict)

        if close:
            self.close_current_connection()

        return installed_solutions_list

    def get_solutions_by_catalog(self, catalog_id, close=True):
        catalog_solutions = []

        cursor = self.get_cursor()
        for row in cursor.execute(
                "SELECT c.* FROM collection c "
                "WHERE c.catalog_id=:catalog_id",
                {
                    "catalog_id": catalog_id
                }
        ).fetchall():
            solution_dict = dict(row)
            self._append_metadata_to_solution(solution_dict)
            catalog_solutions.append(solution_dict)

        if close:
            self.close_current_connection()

        return catalog_solutions

    def _append_metadata_to_solution(self, solution_dict, close=True):
        collection_id = solution_dict["collection_id"]
        solution_dict["authors"] = self._get_authors_by_solution(collection_id)
        solution_dict["tags"] = self._get_tags_by_solution(collection_id)
        solution_dict["cite"] = self._get_citations_by_solution(collection_id)
        solution_dict["args"] = self._get_arguments_by_solution(collection_id)
        solution_dict["covers"] = self._get_covers_by_solution(collection_id)

    def _get_authors_by_solution(self, collection_id, close=True):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT a.* FROM collection_author a "
            "JOIN collection_solution_author sa ON sa.collection_author_id = a.collection_author_id "
            "WHERE sa.collection_id=:collection_id",
            {
                "collection_id": collection_id
            }
        ).fetchall()

        res = []
        for row in r:
            res.append(row["name"])

        if close:
            self.close_current_connection()

        return res

    def _get_arguments_by_solution(self, collection_id, close=True):
        cursor = self.get_cursor()

        r = cursor.execute(
            "SELECT a.* FROM collection_argument a "
            "JOIN collection_solution_argument sa ON sa.collection_argument_id = a.collection_argument_id "
            "WHERE sa.collection_id=:collection_id",
            {
                "collection_id": collection_id
            }
        ).fetchall()

        res = []
        for row in r:
            argument = {"name": row["name"], "type": row["type"], "description": row["description"]}
            if row["default_value"]:
                argument["default_value"] = row["default_value"]
            res.append(argument)

        if close:
            self.close_current_connection()

        return res

    def _get_tags_by_solution(self, collection_id, close=True):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT t.* FROM collection_tag t "
            "JOIN collection_solution_tag st ON st.collection_tag_id = t.collection_tag_id "
            "WHERE st.collection_id=:collection_id",
            {
                "collection_id": collection_id
            }
        ).fetchall()

        res = []
        for row in r:
            res.append(row["name"])

        if close:
            self.close_current_connection()

        return res

    def _get_citations_by_solution(self, collection_id, close=True):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT c.* FROM collection_citation c "
            "JOIN collection_solution_citation sc ON sc.collection_citation_id = c.collection_citation_id "
            "WHERE sc.collection_id=:collection_id",
            {
                "collection_id": collection_id
            }
        ).fetchall()

        res = []
        for row in r:
            citation = {"text": row["text"]}
            if row["doi"]:
                citation["doi"] = row["doi"]
            res.append(citation)

        if close:
            self.close_current_connection()

        return res

    def _get_covers_by_solution(self, collection_id, close=True):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT c.* FROM collection_cover c "
            "WHERE c.collection_id=:collection_id",
            {
                "collection_id": collection_id
            }
        ).fetchall()

        res = []
        for row in r:
            cover = {"description": row["description"], "source": row["source"]}
            res.append(cover)

        if close:
            self.close_current_connection()

        return res

    def get_solution_by_hash(self, hash_value, close=True) -> Optional[dict]:
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM collection WHERE hash=:hash_value",
            {
                "hash_value": hash_value
            }
        ).fetchone()

        solution = None
        if r:
            solution = dict(r)
            self._append_metadata_to_solution(solution)

        if close:
            self.close_current_connection()

        return solution

    def get_solution(self, collection_id, close=True) -> Optional[dict]:
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM collection WHERE collection_id=:collection_id",
            {
                "collection_id": collection_id,
            }).fetchone()

        solution = None
        if r:
            solution = dict(r)
            self._append_metadata_to_solution(solution)

        if close:
            self.close_current_connection()

        return solution

    def get_solution_by_doi(self, doi, close=True) -> Optional[dict]:
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM collection WHERE doi=:doi",
            {
                "doi": doi,
            }).fetchone()

        solution = None
        if r:
            solution = dict(r)
            self._append_metadata_to_solution(solution)

        if close:
            self.close_current_connection()

        return solution

    def get_solution_by_catalog_grp_name_version(self, catalog_id, coordinates: Coordinates, close=True) -> Optional[dict]:
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM collection "
            "WHERE catalog_id=:catalog_id AND \"group\"=:group AND name=:name AND version=:version",
            {
                "catalog_id": catalog_id,
                "group": coordinates.group,
                "name": coordinates.name,
                "version": coordinates.version,
            }
        ).fetchall()

        if len(r) > 1:
            raise KeyError("Database error. Please reinstall the solution %s from catalog %s !"
                           % (coordinates.group, catalog_id))

        installed_solution = None
        for row in r:
            installed_solution = dict(row)
            self._append_metadata_to_solution(installed_solution)

        if close:
            self.close_current_connection()

        return installed_solution

    def get_solutions_by_grp_name_version(self, coordinates: Coordinates, close=True):
        installed_solutions_list = []

        cursor = self.get_cursor()
        for row in cursor.execute(
                "SELECT * FROM collection WHERE \"group\"=:group AND name=:name AND version=:version",
                {
                    "group": coordinates.group,
                    "name": coordinates.name,
                    "version": coordinates.version,
                }
        ).fetchall():
            solution = dict(row)
            self._append_metadata_to_solution(solution)
            installed_solutions_list.append(solution)

        if close:
            self.close_current_connection()

        return installed_solutions_list

    def get_recently_installed_solutions(self, close=True):
        solutions_list = []

        cursor = self.get_cursor()
        for row in cursor.execute("SELECT * FROM collection ORDER BY install_date").fetchall():
            solution = dict(row)
            self._append_metadata_to_solution(solution)
            solutions_list.append(solution)

        if close:
            self.close_current_connection()

        return solutions_list

    def get_recently_launched_solutions(self, close=True):
        solutions_list = []

        cursor = self.get_cursor()
        for row in cursor.execute(
                "SELECT * FROM collection WHERE last_execution IS NOT NULL ORDER BY last_execution"
        ).fetchall():
            solution = dict(row)
            self._append_metadata_to_solution(solution)
            solutions_list.append(solution)

        if close:
            self.close_current_connection()

        return solutions_list

    def update_solution(self, catalog_id, coordinates: Coordinates, solution_attrs, supported_attrs, close=True):
        exec_str = "UPDATE collection SET last_execution=:cur_date"
        exec_args = {
            "cur_date": datetime.now().isoformat(),
            "catalog_id": catalog_id,
            "group": coordinates.group,
            "name": coordinates.name,
            "version": coordinates.version
        }

        for key in supported_attrs:
            if key in solution_attrs:
                col = self._as_db_col(key)
                exec_str += f", {col}=:{key}"
                exec_args[key] = get_dict_entry(solution_attrs, key)

        exec_str += " WHERE catalog_id=:catalog_id AND \"group\"=:group AND name=:name AND version=:version"

        cursor = self.get_cursor()
        cursor.execute(
            exec_str,
            exec_args
        )

        if close:
            self.close_current_connection()

    def add_or_replace_solution(self, catalog_id, coordinates: Coordinates, solution_attrs, close=True):
        solution = self.get_solution_by_catalog_grp_name_version(catalog_id, coordinates, close=False)
        if solution:
            self.remove_solution(catalog_id, coordinates, close=False)
        self.insert_solution(catalog_id, solution_attrs, close=close)

    def remove_solution(self, catalog_id, coordinates: Coordinates, close=True):
        solution = self.get_solution_by_catalog_grp_name_version(catalog_id, coordinates, close=False)
        if not solution:
            return
        solution_id = solution["collection_id"]

        cursor = self.get_cursor()
        cursor.execute(
            "DELETE FROM collection "
            "WHERE catalog_id=:catalog_id AND \"group\"=:group AND name=:name AND version=:version",
            {
                "catalog_id": catalog_id,
                "group": coordinates.group,
                "name": coordinates.name,
                "version": coordinates.version,
            }
        )

        cursor.execute(
            "DELETE FROM collection_cover WHERE collection_id=:collection_id",
            {
                "collection_id": solution_id
            }
        )

        cursor.execute(
            "DELETE FROM collection_solution_tag WHERE collection_id=:collection_id",
            {
                "collection_id": solution_id
            }
        )

        cursor.execute(
            "DELETE FROM collection_solution_author WHERE collection_id=:collection_id",
            {
                "collection_id": solution_id
            }
        )

        cursor.execute(
            "DELETE FROM collection_solution_citation WHERE collection_id=:collection_id",
            {
                "collection_id": solution_id
            }
        )

        cursor.execute(
            "DELETE FROM collection_solution_argument WHERE collection_id=:collection_id",
            {
                "collection_id": solution_id
            }
        )

        cursor.execute(
            "DELETE FROM collection_tag "
            "WHERE NOT EXISTS (SELECT st.collection_tag_id FROM collection_solution_tag st "
            "WHERE collection_tag.collection_tag_id = st.collection_tag_id)")

        cursor.execute(
            "DELETE FROM collection_argument "
            "WHERE NOT EXISTS (SELECT sa.collection_argument_id FROM collection_solution_argument sa "
            "WHERE collection_argument.collection_argument_id = sa.collection_argument_id)")

        cursor.execute(
            "DELETE FROM collection_citation "
            "WHERE NOT EXISTS (SELECT sc.collection_citation_id FROM collection_solution_citation sc "
            "WHERE collection_citation.collection_citation_id = sc.collection_citation_id)")

        cursor.execute(
            "DELETE FROM collection_author "
            "WHERE NOT EXISTS (SELECT sa.collection_author_id FROM collection_solution_author sa "
            "WHERE collection_author.collection_author_id = sa.collection_author_id)")

        if close:
            self.close_current_connection()

    def is_installed(self, catalog_id, coordinates: Coordinates, close=True):
        r = self.get_solution_by_catalog_grp_name_version(catalog_id, coordinates, close=close)
        if not r:
            raise LookupError(f"Solution {catalog_id}:{coordinates} not found!")
        return True if r["installed"] else False

    def remove_catalog(self, catalog_id, close=True):
        cursor = self.get_cursor()
        cursor.execute(
            "DELETE FROM collection "
            "WHERE catalog_id=:catalog_id",
            {
                "catalog_id": catalog_id
            }
        )
        cursor.execute(
            "DELETE FROM collection_solution_tag "
            "WHERE catalog_id=:catalog_id",
            {
                "catalog_id": catalog_id
            }
        )
        cursor.execute(
            "DELETE FROM collection_tag "
            "WHERE catalog_id=:catalog_id",
            {
                "catalog_id": catalog_id
            }
        )
        cursor.execute(
            "DELETE FROM catalog "
            "WHERE catalog_id=:catalog_id",
            {
                "catalog_id": catalog_id
            }
        )

        if close:
            self.close_current_connection()

    def __len__(self, close=True):
        cursor = self.get_cursor()

        r = cursor.execute("SELECT COUNT(*) FROM collection").fetchone()
        r = r[0]

        if close:
            self.close_current_connection()

        return r

    @staticmethod
    def _as_db_col(key):
        if key is "group":
            return "\"group\""
        return key

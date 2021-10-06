import pkgutil
from datetime import datetime

from album.core.concept.database import Database
from album.core.model.coordinates import Coordinates
from album.core.utils.operations.file_operations import get_dict_entry


class CollectionIndex(Database):
    version = "0.1.0"

    def __init__(self, name, path):
        self.name = name
        super().__init__(path)

    def create(self):
        data = pkgutil.get_data('album.core.database', 'catalog_collection_schema.sql')
        self.get_cursor().executescript(data.decode("utf-8"))
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

        for author in solution_attrs["authors"]:
            author_id = self._insert_author(author, catalog_id)
            collection_solution_author_id = self.next_id("collection_solution_author")
            self.get_cursor().execute(
                "INSERT INTO collection_solution_author values (?, ?, ?, ?)",
                (
                    collection_solution_author_id,
                    next_id,
                    author_id,
                    catalog_id
                )
            )

        for tag in solution_attrs["tags"]:
            tag_id = self._insert_tag(tag, catalog_id)
            collection_solution_tag_id = self.next_id("collection_solution_tag")
            self.get_cursor().execute(
                "INSERT INTO collection_solution_tag values (?, ?, ?, ?)",
                (
                    collection_solution_tag_id,
                    next_id,
                    tag_id,
                    catalog_id
                )
            )

        for citation in solution_attrs["cite"]:
            citation_id = self._insert_citation(citation, catalog_id)
            collection_solution_citation_id = self.next_id("collection_solution_citation")
            self.get_cursor().execute(
                "INSERT INTO collection_solution_citation values (?, ?, ?, ?)",
                (
                    collection_solution_citation_id,
                    next_id,
                    citation_id,
                    catalog_id
                )
            )

        for argument in solution_attrs["args"]:
            argument_id = self._insert_argument(argument, catalog_id)
            collection_solution_argument_id = self.next_id("collection_solution_argument")
            self.get_cursor().execute(
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

        self.get_connection().commit()

        return next_id

    def _insert_author(self, author, catalog_id):
        author_id = self.next_id("collection_author")
        self.get_cursor().execute(
            "INSERT INTO collection_author values (?, ?, ?)",
            (
                author_id,
                catalog_id,
                author
            )
        )
        return author_id

    def _insert_tag(self, tag, catalog_id):
        tag_id = self.next_id("collection_tag")
        self.get_cursor().execute(
            "INSERT INTO collection_tag values (?, ?, ?, ?)",
            (
                tag_id,
                catalog_id,
                tag,
                "manual"
            )
        )
        return tag_id

    def _insert_argument(self, argument, catalog_id):
        argument_id = self.next_id("collection_argument")
        self.get_cursor().execute(
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
        return argument_id

    def _insert_citation(self, citation, catalog_id):
        citation_id = self.next_id("collection_citation")
        self.get_cursor().execute(
            "INSERT INTO collection_citation values (?, ?, ?, ?)",
            (
                citation_id,
                catalog_id,
                citation["text"],
                get_dict_entry(citation, "doi")
            )
        )
        return citation_id

    def _insert_cover(self, cover, catalog_id, collection_id):
        cover_id = self.next_id("collection_cover")
        self.get_cursor().execute(
            "INSERT INTO collection_cover values (?, ?, ?, ?, ?)",
            (
                cover_id,
                collection_id,
                catalog_id,
                cover["source"],
                cover["description"]
            )
        )
        return cover_id

    def get_all_solutions(self):
        installed_solutions_list = []
        cursor = self.get_cursor()
        for row in cursor.execute("SELECT * FROM collection").fetchall():
            solution_dict = dict(row)
            self._append_metadata_to_solution(solution_dict)
            installed_solutions_list.append(solution_dict)

        return installed_solutions_list

    def get_solutions_by_catalog(self, catalog_id):
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

        return catalog_solutions

    def _append_metadata_to_solution(self, solution_dict):
        collection_id = solution_dict["collection_id"]
        solution_dict["authors"] = self._get_authors_by_solution(collection_id)
        solution_dict["tags"] = self._get_tags_by_solution(collection_id)
        solution_dict["cite"] = self._get_citations_by_solution(collection_id)
        solution_dict["args"] = self._get_arguments_by_solution(collection_id)
        solution_dict["covers"] = self._get_covers_by_solution(collection_id)

    def _get_authors_by_solution(self, collection_id):
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
        return res

    def _get_arguments_by_solution(self, collection_id):
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
            if row["default_value"]: argument["default_value"] = row["default_value"]
            res.append(argument)
        return res

    def _get_tags_by_solution(self, collection_id):
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
        return res

    def _get_citations_by_solution(self, collection_id):
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
            if row["doi"]: citation["doi"] = row["doi"]
            res.append(citation)
        return res

    def _get_covers_by_solution(self, collection_id):
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
        return res

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
            self._append_metadata_to_solution(solution)

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
            self._append_metadata_to_solution(solution)

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
            self._append_metadata_to_solution(solution)

        return solution

    def get_solution_by_catalog_grp_name_version(self, catalog_id, coordinates: Coordinates):
        r = self.get_cursor().execute(
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

        return installed_solution

    def get_solutions_by_grp_name_version(self, coordinates: Coordinates):
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

        return installed_solutions_list

    def get_recently_installed_solutions(self):
        solutions_list = []
        cursor = self.get_cursor()
        for row in cursor.execute("SELECT * FROM collection ORDER BY install_date").fetchall():
            solution = dict(row)
            self._append_metadata_to_solution(solution)
            solutions_list.append(solution)
        return solutions_list

    def get_recently_launched_solutions(self):
        solutions_list = []
        cursor = self.get_cursor()
        for row in cursor.execute("SELECT * FROM collection WHERE last_execution IS NOT NULL ORDER BY last_execution").fetchall():
            solution = dict(row)
            self._append_metadata_to_solution(solution)
            solutions_list.append(solution)
        return solutions_list

    def update_solution(self, catalog_id, coordinates: Coordinates, solution_attrs, supported_attrs):
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

        self.get_cursor().execute(
            exec_str,
            exec_args
        )

        self.get_connection().commit()

    def add_or_replace_solution(self, catalog_id, coordinates: Coordinates, solution_attrs, supported_attrs):
        solution = self.get_solution_by_catalog_grp_name_version(catalog_id, coordinates)
        if solution:
            self.remove_solution(catalog_id, coordinates)
        self.insert_solution(catalog_id, solution_attrs)

    def remove_solution(self, catalog_id, coordinates: Coordinates):
        solution = self.get_solution_by_catalog_grp_name_version(catalog_id, coordinates)
        if not solution:
            return
        solution_id = solution["collection_id"]
        self.get_cursor().execute(
            "DELETE FROM collection "
            "WHERE catalog_id=:catalog_id AND \"group\"=:group AND name=:name AND version=:version",
            {
                "catalog_id": catalog_id,
                "group": coordinates.group,
                "name": coordinates.name,
                "version": coordinates.version,
            }
        )

        self.get_cursor().execute(
            "DELETE FROM collection_cover WHERE collection_id=:collection_id",
            {
                "collection_id": solution_id
            }
        )

        self.get_cursor().execute(
            "DELETE FROM collection_solution_tag WHERE collection_id=:collection_id",
            {
                "collection_id": solution_id
            }
        )

        self.get_cursor().execute(
            "DELETE FROM collection_solution_author WHERE collection_id=:collection_id",
            {
                "collection_id": solution_id
            }
        )

        self.get_cursor().execute(
            "DELETE FROM collection_solution_citation WHERE collection_id=:collection_id",
            {
                "collection_id": solution_id
            }
        )

        self.get_cursor().execute(
            "DELETE FROM collection_solution_argument WHERE collection_id=:collection_id",
            {
                "collection_id": solution_id
            }
        )

        self.get_cursor().execute(
            "DELETE FROM collection_tag "
            "WHERE NOT EXISTS (SELECT st.collection_tag_id FROM collection_solution_tag st "
            "WHERE collection_tag.collection_tag_id = st.collection_tag_id)")

        self.get_cursor().execute(
            "DELETE FROM collection_argument "
            "WHERE NOT EXISTS (SELECT sa.collection_argument_id FROM collection_solution_argument sa "
            "WHERE collection_argument.collection_argument_id = sa.collection_argument_id)")

        self.get_cursor().execute(
            "DELETE FROM collection_citation "
            "WHERE NOT EXISTS (SELECT sc.collection_citation_id FROM collection_solution_citation sc "
            "WHERE collection_citation.collection_citation_id = sc.collection_citation_id)")

        self.get_cursor().execute(
            "DELETE FROM collection_author "
            "WHERE NOT EXISTS (SELECT sa.collection_author_id FROM collection_solution_author sa "
            "WHERE collection_author.collection_author_id = sa.collection_author_id)")

        self.get_connection().commit()

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

    def is_installed(self, catalog_id, coordinates: Coordinates):
        r = self.get_solution_by_catalog_grp_name_version(catalog_id, coordinates)
        if not r:
            raise LookupError(f"Solution {catalog_id}:{coordinates} not found!")
        return True if r["installed"] else False

    # ### catalog_collection features ###

    def remove_catalog(self, catalog_id):
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
        self.get_connection().commit()

    def __len__(self):
        r = self.get_cursor().execute("SELECT COUNT(*) FROM collection").fetchone()
        r = r[0]

        return r

    @staticmethod
    def _as_db_col(key):
        if key is "group":
            return "\"group\""
        return key

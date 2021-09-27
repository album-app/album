import datetime
import hashlib
import json
import pkgutil
from typing import Optional

from album.core.concept.database import Database
from album.core.model.identity import Identity
from album.core.utils.operations.file_operations import get_dict_entry, write_dict_to_json
from album.core.utils.operations.resolve_operations import dict_to_identity


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
        data = pkgutil.get_data('album.core.database', 'catalog_index_schema.sql')
        self.get_cursor().executescript(data.decode("utf-8"))
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

    def get_all_solutions(self):
        r = self.get_cursor().execute(
            "SELECT * FROM solution",
            {}).fetchall()

        solutions = []
        if r:
            for s in r:
                solution = dict(s)
                self._append_metadata_to_solution_dict(solution)
                solutions.append(solution)
        return solutions

    def _insert_solution(self, solution_attrs) -> int:
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
        for author in solution_attrs["authors"]:
            author_id = self._insert_author(author)
            solution_author_id = self.next_id("solution_author")
            self.get_cursor().execute(
                "INSERT INTO solution_author values (?, ?, ?)",
                (
                    solution_author_id,
                    solution_id,
                    author_id
                )
            )
        for tag in solution_attrs["tags"]:
            tag_id = self._insert_tag(tag)
            solution_tag_id = self.next_id("solution_tag")
            self.get_cursor().execute(
                "INSERT INTO solution_tag values (?, ?, ?)",
                (
                    solution_tag_id,
                    solution_id,
                    tag_id
                )
            )
        for argument in solution_attrs["args"]:
            argument_id = self._insert_argument(argument)
            solution_argument_id = self.next_id("solution_argument")
            self.get_cursor().execute(
                "INSERT INTO solution_argument values (?, ?, ?)",
                (
                    solution_argument_id,
                    solution_id,
                    argument_id
                )
            )
        for citation in solution_attrs["cite"]:
            citation_id = self._insert_citation(citation)
            solution_citation_id = self.next_id("solution_citation")
            self.get_cursor().execute(
                "INSERT INTO solution_citation values (?, ?, ?)",
                (
                    solution_citation_id,
                    solution_id,
                    citation_id
                )
            )
        for cover in solution_attrs["covers"]:
            self._insert_cover(cover, solution_id)
        self.save()
        return solution_id

    def _insert_author(self, author):
        author_id = self.next_id("author")
        self.get_cursor().execute(
            "INSERT INTO author values (?, ?)",
            (
                author_id,
                author
            )
        )
        return author_id

    def _insert_tag(self, tag):
        tag_id = self.next_id("tag")
        self.get_cursor().execute(
            "INSERT INTO tag values (?, ?, ?)",
            (
                tag_id,
                tag,
                "manual"
            )
        )
        return tag_id

    def _insert_argument(self, argument):
        argument_id = self.next_id("argument")
        self.get_cursor().execute(
            "INSERT INTO argument values (?, ?, ?, ?, ?)",
            (
                argument_id,
                argument["name"],
                get_dict_entry(argument, "type"),
                argument["description"],
                get_dict_entry(argument, "default_value")
            )
        )
        return argument_id

    def _insert_citation(self, citation):
        citation_id = self.next_id("citation")
        self.get_cursor().execute(
            "INSERT INTO citation values (?, ?, ?)",
            (
                citation_id,
                citation["text"],
                get_dict_entry(citation, "doi")
            )
        )
        return citation_id

    def _insert_cover(self, cover, solution_id):
        cover_id = self.next_id("cover")
        self.get_cursor().execute(
            "INSERT INTO cover values (?, ?, ?, ?)",
            (
                cover_id,
                solution_id,
                cover["source"],
                cover["description"]
            )
        )
        return cover_id

    def get_solution(self, solution_id) -> Optional[dict]:
        r = self.get_cursor().execute(
            "SELECT * FROM solution WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id,
            }).fetchone()
        solution = None
        if r:
            solution = dict(r)
            self._append_metadata_to_solution_dict(solution)
        return solution

    def get_solution_by_group_name_version(self, identity: Identity) -> Optional[dict]:
        """Resolves a solution by its name, version and group.

        Args:
            identity:
                The group affiliation, name, and version of the solution.

        Returns:
            None or row not found.

        """
        cursor = self.get_cursor()

        r = cursor.execute(
            "SELECT s.* FROM solution s "
            "WHERE s.\"group\"=:group AND s.name=:name AND s.version=:version",
            {
                "group": identity.group,
                "name": identity.name,
                "version": identity.version,
            }
        ).fetchone()

        solution = None
        if r:
            solution = dict(r)
            self._append_metadata_to_solution_dict(solution)
        return solution

    def _append_metadata_to_solution_dict(self, solution):
        solution_id = solution["solution_id"]
        solution["authors"] = self._get_authors_by_solution(solution_id)
        solution["covers"] = self._get_covers_by_solution(solution_id)
        solution["args"] = self._get_arguments_by_solution(solution_id)
        solution["cite"] = self._get_citations_by_solution(solution_id)
        solution["tags"] = self._get_tags_by_solution(solution_id)

    def get_solution_by_doi(self, doi) -> Optional[dict]:
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

    def _update_solution(self, solution_attrs) -> None:
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
        self.save()

    def remove_solution(self, solution_id):
        self.get_cursor().execute(
            "DELETE FROM solution WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        )
        self.get_cursor().execute(
            "DELETE FROM cover WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        )

        self.get_cursor().execute(
            "DELETE FROM solution_tag WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        )

        self.get_cursor().execute(
            "DELETE FROM solution_author WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        )

        self.get_cursor().execute(
            "DELETE FROM solution_citation WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        )

        self.get_cursor().execute(
            "DELETE FROM solution_argument WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        )

        self.get_cursor().execute(
            "DELETE FROM tag "
            "WHERE NOT EXISTS (SELECT st.tag_id FROM solution_tag st "
            "WHERE tag.tag_id = st.tag_id)")

        self.get_cursor().execute(
            "DELETE FROM argument "
            "WHERE NOT EXISTS (SELECT sa.argument_id FROM solution_argument sa "
            "WHERE argument.argument_id = sa.argument_id)")

        self.get_cursor().execute(
            "DELETE FROM citation "
            "WHERE NOT EXISTS (SELECT sc.citation_id FROM solution_citation sc "
            "WHERE citation.citation_id = sc.citation_id)")

        self.get_cursor().execute(
            "DELETE FROM author "
            "WHERE NOT EXISTS (SELECT sa.author_id FROM solution_author sa "
            "WHERE author.author_id = sa.author_id)")

        self.save()

    def remove_solution_by_group_name_version(self, identity: Identity):
        solution_dict = self.get_solution_by_group_name_version(identity)
        if solution_dict:
            self.remove_solution(solution_dict["solution_id"])

    # ### catalog_features ###

    def update(self, solution_attrs: dict):
        """Updates a catalog to include a solution as a node with the attributes given.
         Updates exiting nodes if node already present in tree.

        Args:
            solution_attrs:
                The solution attributes. Must hold group, name, version.

        """
        if self.get_solution_by_group_name_version(dict_to_identity(solution_attrs)):
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
                self._append_metadata_to_solution_dict(solution)
                json_dumps_list.append(json.dumps(solution))

            write_dict_to_json(path, json_dumps_list)
        else:
            raise NotImplementedError("Unsupported format \"%s\"" % export_format)

    def __len__(self):
        r = self.get_cursor().execute("SELECT COUNT(*) FROM solution").fetchone()
        r = r[0]

        return r

    def _get_authors_by_solution(self, solution_id):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT a.* FROM author a "
            "JOIN solution_author sa ON sa.author_id = a.author_id "
            "WHERE sa.solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        ).fetchall()

        res = []
        for row in r:
            res.append(row["name"])

        return res

    def _get_tags_by_solution(self, solution_id):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT t.* FROM tag t "
            "JOIN solution_tag st ON st.tag_id = t.tag_id "
            "WHERE st.solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        ).fetchall()

        res = []
        for row in r:
            res.append(row["name"])

        return res

    def _get_citations_by_solution(self, solution_id):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT c.* FROM citation c "
            "JOIN solution_citation sc ON sc.citation_id = c.citation_id "
            "WHERE sc.solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        ).fetchall()

        res = []
        for row in r:
            res.append(dict(row))

        return res

    def _get_arguments_by_solution(self, solution_id):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT a.* FROM argument a "
            "JOIN solution_argument sa ON sa.argument_id = a.argument_id "
            "WHERE sa.solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        ).fetchall()

        res = []
        for row in r:
            res.append(dict(row))

        return res

    def _get_covers_by_solution(self, solution_id):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT c.* FROM cover c "
            "WHERE c.solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        ).fetchall()

        res = []
        for row in r:
            res.append(dict(row))

        return res

    @staticmethod
    def create_hash(string_representation):
        hash_val = hashlib.md5(string_representation.encode('utf-8')).hexdigest()

        return hash_val

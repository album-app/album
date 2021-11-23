import json
import pkgutil
from datetime import datetime
from typing import Optional

from album.core.concept.database import Database
from album.core.utils.operations.file_operations import get_dict_entry, write_dict_to_json
from album.core.utils.operations.solution_operations import get_solution_hash
from album.runner import album_logging
from album.runner.model.coordinates import Coordinates

module_logger = album_logging.get_active_logger


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
        data = pkgutil.get_data('album.core.schema', 'catalog_index_schema.sql')

        cursor = self.get_cursor()
        cursor.executescript(data.decode("utf-8"))

        self.update_name_version(self.name, self.version, close=False)

        # explicitly commit and close
        self.close_current_connection(commit=True)

    def is_empty(self, close=True):
        cursor = self.get_cursor()
        r = cursor.execute("SELECT * FROM solution").fetchone()

        if close:
            self.close_current_connection()

        return False if r else True

    # ### catalog_index ###

    def update_name_version(self, name, version, close=True):
        module_logger().debug("Update index name: \"%s\" and version: \"%s\"" % (name, version))

        curr_name = self.get_name()

        cursor = self.get_cursor()
        if curr_name:
            cursor.execute(
                "UPDATE catalog_index SET name=:name, version=:version WHERE name_id=:name_id",
                {"name_id": 1, "name": name, "version": version}
            )
        else:
            cursor.execute(
                "INSERT INTO catalog_index values (?, ?, ?)",
                (1, name, version)
            )

        if close:
            self.close_current_connection()

    def get_name(self, close=True):
        module_logger().debug("Get catalog name")

        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM catalog_index"
        ).fetchone()

        cur_name = r["name"] if r else None

        if close:
            self.close_current_connection()

        return cur_name

    def get_version(self, close=True):
        module_logger().debug("Get index version...")

        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM catalog_index"
        ).fetchone()

        cur_version = r["version"] if r else None

        if close:
            self.close_current_connection()

        return cur_version

    def get_all_solutions(self, close=True):
        module_logger().debug("Retrieve all solutions")

        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM solution",
            {}).fetchall()

        solutions = []
        if r:
            for s in r:
                solution = dict(s)
                self._append_metadata_to_solution_dict(solution)
                solutions.append(solution)

        if close:
            self.close_current_connection()

        return solutions

    @staticmethod
    def get_solution_column_keys():
        return ['group', 'name', 'description', 'version', 'album_api_version', 'album_version', 'license',
                'acknowledgement', 'title', 'timestamp']

    def _insert_solution(self, solution_attrs, close=True) -> int:
        hash_val = get_solution_hash(solution_attrs, self.get_solution_column_keys())
        solution_id = self.next_id("solution")

        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO solution values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                solution_id,
                solution_attrs["group"],
                solution_attrs["name"],
                solution_attrs["title"],
                solution_attrs["version"],
                datetime.now().isoformat(),
                solution_attrs["description"],
                get_dict_entry(solution_attrs, "doi"),  # allow to be none
                solution_attrs["license"],
                solution_attrs["album_version"],
                solution_attrs["album_api_version"],
                get_dict_entry(solution_attrs, "changelog"),  # allow to be none
                get_dict_entry(solution_attrs, "acknowledgement"),
                hash_val
            )
        )
        for author in solution_attrs["authors"]:
            author_id = self._insert_author(author, close=False)
            solution_author_id = self.next_id("solution_author")
            cursor.execute(
                "INSERT INTO solution_author values (?, ?, ?)",
                (
                    solution_author_id,
                    solution_id,
                    author_id
                )
            )
        for tag in solution_attrs["tags"]:
            tag_id = self._insert_tag(tag, close=False)
            solution_tag_id = self.next_id("solution_tag")
            cursor.execute(
                "INSERT INTO solution_tag values (?, ?, ?)",
                (
                    solution_tag_id,
                    solution_id,
                    tag_id
                )
            )
        for argument in solution_attrs["args"]:
            argument_id = self._insert_argument(argument, close=False)
            solution_argument_id = self.next_id("solution_argument")
            cursor.execute(
                "INSERT INTO solution_argument values (?, ?, ?)",
                (
                    solution_argument_id,
                    solution_id,
                    argument_id
                )
            )
        for citation in solution_attrs["cite"]:
            citation_id = self._insert_citation(citation, close=False)
            solution_citation_id = self.next_id("solution_citation")
            cursor.execute(
                "INSERT INTO solution_citation values (?, ?, ?)",
                (
                    solution_citation_id,
                    solution_id,
                    citation_id
                )
            )
        for cover in solution_attrs["covers"]:
            self._insert_cover(cover, solution_id, close=False)

        for documentation in solution_attrs["documentation"]:
            self._insert_documentation(documentation, solution_id, close=False)

        self.save()

        if close:
            self.close_current_connection()

        return solution_id

    def _insert_author(self, author, close=True):
        author_id = self.next_id("author")

        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO author values (?, ?)",
            (
                author_id,
                author
            )
        )

        if close:
            self.close_current_connection()

        return author_id

    def _insert_tag(self, tag, close=True):
        tag_id = self.next_id("tag")

        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO tag values (?, ?, ?)",
            (
                tag_id,
                tag,
                "manual"
            )
        )

        if close:
            self.close_current_connection()

        return tag_id

    def _insert_argument(self, argument, close=True):
        argument_id = self.next_id("argument")

        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO argument values (?, ?, ?, ?, ?, ?)",
            (
                argument_id,
                argument["name"],
                get_dict_entry(argument, "type"),
                argument["description"],
                get_dict_entry(argument, "default_value"),
                get_dict_entry(argument, "required")
            )
        )

        if close:
            self.close_current_connection()

        return argument_id

    def _insert_citation(self, citation, close=True):
        citation_id = self.next_id("citation")
        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO citation values (?, ?, ?, ?)",
            (
                citation_id,
                citation["text"],
                get_dict_entry(citation, "doi"),
                get_dict_entry(citation, "url")
            )
        )

        if close:
            self.close_current_connection()

        return citation_id

    def _insert_cover(self, cover, solution_id, close=True):
        cover_id = self.next_id("cover")

        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO cover values (?, ?, ?, ?)",
            (
                cover_id,
                solution_id,
                cover["source"],
                cover["description"]
            )
        )

        if close:
            self.close_current_connection()

        return cover_id

    def _insert_documentation(self, documentation, solution_id, close=True):
        documentation_id = self.next_id("documentation")
        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO documentation values (?, ?, ?)",
            (
                documentation_id,
                solution_id,
                documentation
            )
        )

        if close:
            self.close_current_connection()

        return documentation_id

    def get_solution(self, solution_id, close=True) -> Optional[dict]:
        module_logger().debug("Get solution by id: \"%s\"..." % solution_id)

        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM solution WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id,
            }).fetchone()
        solution = None
        if r:
            solution = dict(r)
            self._append_metadata_to_solution_dict(solution)

        if close:
            self.close_current_connection()

        return solution

    def get_solution_by_coordinates(self, coordinates: Coordinates, close=True) -> Optional[dict]:
        """Resolves a solution by its name, version and group.

        Args:
            close:
                if specified closes the connection after execution
            coordinates:
                The group affiliation, name, and version of the solution.

        Returns:
            None or row not found.

        """
        module_logger().debug("Get solution by coordinates: \"%s\"..." % str(coordinates))

        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT s.* FROM solution s "
            "WHERE s.\"group\"=:group AND s.name=:name AND s.version=:version",
            {
                "group": coordinates.group,
                "name": coordinates.name,
                "version": coordinates.version,
            }
        ).fetchone()

        solution = None
        if r:
            solution = dict(r)
            self._append_metadata_to_solution_dict(solution)

        if close:
            self.close_current_connection()

        return solution

    def _append_metadata_to_solution_dict(self, solution):
        solution_id = solution["solution_id"]
        solution["authors"] = self._get_authors_by_solution(solution_id)
        solution["covers"] = self._get_covers_by_solution(solution_id)
        solution["documentation"] = self._get_documentation_by_solution(solution_id)
        solution["args"] = self._get_arguments_by_solution(solution_id)
        solution["cite"] = self._get_citations_by_solution(solution_id)
        solution["tags"] = self._get_tags_by_solution(solution_id)

    def get_solution_by_doi(self, doi, close=True) -> Optional[dict]:
        """Resolves a solution by its DOI.

        Args:
            close:
                if speficied closes the connection after execution
            doi:
                The doi to resolve for.

        Returns:
            None or a node if any found.

        Raises:
            RuntimeError if the DOI was found more than once.
                         if the node found is not a leaf

        """
        module_logger().debug("Get solution by doi: \"%s\"..." % doi)

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

        if close:
            self.close_current_connection()

        return solution

    def _update_solution(self, solution_attrs, close=True) -> None:
        hash_val = get_solution_hash(solution_attrs, self.get_solution_column_keys())

        cursor = self.get_cursor()
        cursor.execute(
            "UPDATE solution SET "
            "title=:title, "
            "timestamp=:timestamp, "
            "description=:description, "
            "doi=:doi, "
            "acknowledgement=:acknowledgement, "
            "license=:license, "
            "album_version=:album_version, "
            "album_api_version=:album_api_version, "
            "changelog=:changelog,"
            "hash=:hash_val "
            "WHERE \"group\"=:group AND name=:name AND version=:version",
            {
                "group": solution_attrs["group"],
                "name": solution_attrs["name"],
                "version": solution_attrs["version"],
                "title": solution_attrs["title"],
                "timestamp": "",
                "description": solution_attrs["description"],
                "doi": get_dict_entry(solution_attrs, "doi"),
                "acknowledgement": solution_attrs["acknowledgement"],
                "license": solution_attrs["license"],
                "album_version": solution_attrs["album_version"],
                "album_api_version": solution_attrs["album_api_version"],
                "changelog": get_dict_entry(solution_attrs, "changelog"),
                "hash_val": hash_val
            }
        )
        self.save()

        if close:
            self.close_current_connection()

    def remove_solution(self, solution_id, close=True):
        cursor = self.get_cursor()

        cursor.execute(
            "DELETE FROM cover WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        )
        cursor.execute(
            "DELETE FROM documentation WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        )

        cursor.execute(
            "DELETE FROM solution_tag WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        )

        cursor.execute(
            "DELETE FROM solution_author WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        )

        cursor.execute(
            "DELETE FROM solution_citation WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        )

        cursor.execute(
            "DELETE FROM solution_argument WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        )

        cursor.execute(
            "DELETE FROM tag "
            "WHERE NOT EXISTS (SELECT st.tag_id FROM solution_tag st "
            "WHERE tag.tag_id = st.tag_id)")

        cursor.execute(
            "DELETE FROM argument "
            "WHERE NOT EXISTS (SELECT sa.argument_id FROM solution_argument sa "
            "WHERE argument.argument_id = sa.argument_id)")

        cursor.execute(
            "DELETE FROM citation "
            "WHERE NOT EXISTS (SELECT sc.citation_id FROM solution_citation sc "
            "WHERE citation.citation_id = sc.citation_id)")

        cursor.execute(
            "DELETE FROM author "
            "WHERE NOT EXISTS (SELECT sa.author_id FROM solution_author sa "
            "WHERE author.author_id = sa.author_id)")

        cursor.execute(
            "DELETE FROM solution WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        )

        self.save()

        if close:
            self.close_current_connection()

    def remove_solution_by_group_name_version(self, coordinates: Coordinates, close=True):
        solution_dict = self.get_solution_by_coordinates(coordinates, close=close)
        if solution_dict:
            self.remove_solution(solution_dict["solution_id"])

    # ### catalog_features ###

    def update(self, coordinates: Coordinates, solution_attrs: dict, close=True):
        """Updates a catalog to include a solution as a node with the attributes given.
         Updates exiting nodes if node already present in tree.

        Args:
            close:
                if speficied closes the connection after execution
            coordinates:
                The coordinates of the solution.
            solution_attrs:
                The solution attributes. Must hold group, name, version.

        """
        if self.get_solution_by_coordinates(coordinates, close=False):
            module_logger().debug("Update solution...")
            self._update_solution(solution_attrs, close=close)
        else:
            module_logger().debug("Insert solution...")
            self._insert_solution(solution_attrs, close=close)

    def save(self):
        module_logger().debug("Saving index...")
        self.get_connection().commit()

    def export(self, path, export_format="JSON", close=True):
        """Exports the index tree to disk.

        Args:
            close:
                if speficied closes the connection after execution
            path:
                The path to store the export to.
            export_format:
                The format to save to. Choose from ["JSON"]. (Default: JSON)

        Raises:
            NotImplementedError if the format is not supported.

        """
        module_logger().debug("Export index...")

        cursor = self.get_cursor()
        r = cursor.execute("SELECT * FROM solution").fetchall()

        if export_format == "JSON":
            json_dumps_list = []
            for solution in r:
                solution = dict(solution)
                self._append_metadata_to_solution_dict(solution)
                json_dumps_list.append(json.dumps(solution))

            write_dict_to_json(path, json_dumps_list)
        else:
            raise NotImplementedError("Unsupported format \"%s\"" % export_format)

        if close:
            self.close_current_connection()

    def __len__(self, close=True):
        cursor = self.get_cursor()
        r = cursor.execute("SELECT COUNT(*) FROM solution").fetchone()
        r = r[0]

        if close:
            self.close_current_connection()

        return r

    def _get_authors_by_solution(self, solution_id, close=True):
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

        if close:
            self.close_current_connection()

        return res

    def _get_tags_by_solution(self, solution_id, close=True):
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

        if close:
            self.close_current_connection()

        return res

    def _get_citations_by_solution(self, solution_id, close=True):
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

        if close:
            self.close_current_connection()

        return res

    def _get_arguments_by_solution(self, solution_id, close=True):
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

        if close:
            self.close_current_connection()

        return res

    def _get_covers_by_solution(self, solution_id, close=True):
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

        if close:
            self.close_current_connection()

        return res

    def _get_documentation_by_solution(self, solution_id, close=True):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT d.* FROM documentation d "
            "WHERE d.solution_id=:solution_id",
            {
                "solution_id": solution_id
            }
        ).fetchall()

        res = []
        for row in r:
            res.append(row["documentation"])

        if close:
            self.close_current_connection()

        return res

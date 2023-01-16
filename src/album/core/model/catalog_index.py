import pkgutil
from datetime import datetime
from typing import Optional, List

from album.core.api.model.catalog_index import ICatalogIndex
from album.core.model.database import Database
from album.core.utils.operations.file_operations import (
    get_dict_entry,
    write_dict_to_json,
)
from album.core.utils.operations.solution_operations import (
    get_solution_hash,
    serialize_json,
)
from album.runner import album_logging
from album.runner.core.api.model.coordinates import ICoordinates
from album.core.model.default_values import DefaultValues

module_logger = album_logging.get_active_logger


class CatalogIndex(ICatalogIndex, Database):

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
        data = pkgutil.get_data("album.core.schema", "catalog_index_schema.sql")

        cursor = self.get_cursor()
        cursor.executescript(data.decode("utf-8"))

        self.update_name_version(self.name, DefaultValues.catalog_index_db_version.value, close=False)

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
        module_logger().debug(
            'Update index name: "%s" and version: "%s"' % (name, version)
        )

        curr_name = self.get_name()

        cursor = self.get_cursor()
        if curr_name:
            cursor.execute(
                "UPDATE catalog_index SET name=:name, version=:version WHERE name_id=:name_id",
                {"name_id": 1, "name": name, "version": version},
            )
        else:
            cursor.execute(
                "INSERT INTO catalog_index values (?, ?, ?)", (1, name, version)
            )

        if close:
            self.close_current_connection()

    def get_name(self, close=True):
        module_logger().debug("Get catalog name...")

        cursor = self.get_cursor()
        r = cursor.execute("SELECT * FROM catalog_index").fetchone()

        cur_name = r["name"] if r else None

        if close:
            self.close_current_connection()

        return cur_name

    def get_version(self, close=True):
        module_logger().debug("Get index version...")

        cursor = self.get_cursor()
        r = cursor.execute("SELECT * FROM catalog_index").fetchone()

        cur_version = r["version"] if r else None

        if close:
            self.close_current_connection()

        return cur_version

    def get_all_solutions(self, close=True):
        module_logger().debug("Retrieve all solutions...")

        cursor = self.get_cursor()
        r = cursor.execute("SELECT * FROM solution", {}).fetchall()

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
        return [
            "group",
            "name",
            "description",
            "version",
            "album_api_version",
            "album_version",
            "license",
            "acknowledgement",
            "title",
            "timestamp",
            "doi",
            "changelog",
        ]

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
                get_dict_entry(solution_attrs, "title"),
                solution_attrs["version"],
                datetime.now().isoformat(),
                get_dict_entry(solution_attrs, "description"),
                get_dict_entry(solution_attrs, "doi"),  # allow to be none
                get_dict_entry(solution_attrs, "license"),
                get_dict_entry(solution_attrs, "album_version"),
                get_dict_entry(solution_attrs, "album_api_version"),
                get_dict_entry(solution_attrs, "changelog"),  # allow to be none
                get_dict_entry(solution_attrs, "acknowledgement"),
                hash_val,
            ),
        )
        if "solution_creators" in solution_attrs:
            for author in solution_attrs["solution_creators"]:
                author_id = self._exists_author(author, close=False)
                if not author_id:
                    author_id = self._insert_author(author, close=False)
                solution_author_id = self.next_id("solution_author")
                cursor.execute(
                    "INSERT INTO solution_author values (?, ?, ?)",
                    (solution_author_id, solution_id, author_id),
                )

        if "tags" in solution_attrs:
            for tag in solution_attrs["tags"]:
                tag_id = self._exists_tag(tag, close=False)
                if not tag_id:
                    tag_id = self._insert_tag(tag, close=False)
                solution_tag_id = self.next_id("solution_tag")
                cursor.execute(
                    "INSERT INTO solution_tag values (?, ?, ?)",
                    (solution_tag_id, solution_id, tag_id),
                )

        if "args" in solution_attrs:
            for argument in solution_attrs["args"]:
                argument_id = self._exists_argument(argument, close=False)
                if not argument_id:
                    argument_id = self._insert_argument(argument, close=False)
                solution_argument_id = self.next_id("solution_argument")
                cursor.execute(
                    "INSERT INTO solution_argument values (?, ?, ?)",
                    (solution_argument_id, solution_id, argument_id),
                )
        if "cite" in solution_attrs:
            for citation in solution_attrs["cite"]:
                citation_id = self._exists_citation(citation, close=False)
                if not citation_id:
                    citation_id = self._insert_citation(citation, close=False)
                solution_citation_id = self.next_id("solution_citation")
                cursor.execute(
                    "INSERT INTO solution_citation values (?, ?, ?)",
                    (solution_citation_id, solution_id, citation_id),
                )

        if "custom" in solution_attrs:
            for key in solution_attrs["custom"]:
                value = solution_attrs["custom"][key]
                custom_id = self._exists_custom_key(key, value, close=False)
                if not custom_id:
                    custom_id = self._insert_custom_key(key, value, close=False)
                solution_custom_key_id = self.next_id("solution_custom")
                cursor.execute(
                    "INSERT INTO solution_custom values (?, ?, ?)",
                    (solution_custom_key_id, solution_id, custom_id),
                )

        if "covers" in solution_attrs:
            for cover in solution_attrs["covers"]:
                if not self._exists_cover(cover, solution_id):
                    self._insert_cover(cover, solution_id, close=False)

        if "documentation" in solution_attrs:
            for documentation in solution_attrs["documentation"]:
                if not self._exists_documentation(documentation, solution_id):
                    self._insert_documentation(documentation, solution_id, close=False)

        self.save()

        if close:
            self.close_current_connection()

        return solution_id

    def _exists_author(self, author_name, close=True):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM author WHERE name=:author_name", {"author_name": author_name}
        ).fetchone()

        if close:
            self.close_current_connection()

        return r["author_id"] if r else None

    def _insert_author(self, author, close=True):
        author_id = self.next_id("author")

        cursor = self.get_cursor()
        cursor.execute("INSERT INTO author values (?, ?)", (author_id, author))

        if close:
            self.close_current_connection()

        return author_id

    def _exists_tag(self, tag_name, close=True):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM tag WHERE name=:tag_name ", {"tag_name": tag_name}
        ).fetchone()

        if close:
            self.close_current_connection()

        return r["tag_id"] if r else None

    def _insert_tag(self, tag, close=True):
        tag_id = self.next_id("tag")

        cursor = self.get_cursor()
        cursor.execute("INSERT INTO tag values (?, ?, ?)", (tag_id, tag, "manual"))

        if close:
            self.close_current_connection()

        return tag_id

    def _exists_argument(self, argument, close=True):
        cursor = self.get_cursor()

        exc_str = "SELECT * FROM argument WHERE name=:argument_name AND description=:argument_description "
        exc_val = {
            "argument_name": argument["name"],
            "argument_description": argument["description"],
        }
        argument_type = get_dict_entry(argument, "type")
        argument_default_value = get_dict_entry(argument, "default")

        if argument_type:
            exc_str += "AND type=:argument_type "
            exc_val["argument_type"] = argument_type
        else:
            exc_str += "AND type IS NULL "

        if argument_default_value:
            exc_str += "AND default_value=:argument_default_value "
            exc_val["argument_default_value"] = argument_default_value
        else:
            exc_str += "AND default_value IS NULL "

        r = cursor.execute(exc_str, exc_val).fetchone()

        if close:
            self.close_current_connection()

        return r["argument_id"] if r else None

    def _exists_custom_key(self, custom_key, custom_value, close=True):
        cursor = self.get_cursor()

        exc_str = "SELECT * FROM custom WHERE custom_key=:custom_key AND custom_value=:custom_value "
        exc_val = {
            "custom_key": custom_key,
            "custom_value": custom_value,
        }

        r = cursor.execute(exc_str, exc_val).fetchone()

        if close:
            self.close_current_connection()

        return r["custom_id"] if r else None

    def _insert_argument(self, argument, close=True):
        argument_id = self.next_id("argument")

        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO argument values (?, ?, ?, ?, ?, ?)",
            (
                argument_id,
                argument["name"],
                get_dict_entry(argument, "type"),
                get_dict_entry(argument, "description"),
                get_dict_entry(argument, "default"),
                get_dict_entry(argument, "required"),
            ),
        )

        if close:
            self.close_current_connection()

        return argument_id

    def _insert_custom_key(self, custom_key, custom_value, close=True):
        custom_id = self.next_id("custom")

        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO custom values (?, ?, ?)", (custom_id, custom_key, custom_value)
        )

        if close:
            self.close_current_connection()

        return custom_id

    def _exists_citation(self, citation, close=True):
        cursor = self.get_cursor()

        exc_str = "SELECT * FROM citation WHERE text=:citation_text "
        exc_val = {
            "citation_text": citation["text"],
        }
        citation_doi = get_dict_entry(citation, "doi")

        if citation_doi:
            exc_str += "AND doi=:citation_doi"
            exc_val["citation_doi"] = citation_doi
        else:
            exc_str += "AND doi IS NULL"

        r = cursor.execute(exc_str, exc_val).fetchone()

        if close:
            self.close_current_connection()

        return r["citation_id"] if r else None

    def _insert_citation(self, citation, close=True):
        citation_id = self.next_id("citation")
        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO citation values (?, ?, ?, ?)",
            (
                citation_id,
                citation["text"],
                get_dict_entry(citation, "doi"),
                get_dict_entry(citation, "url"),
            ),
        )

        if close:
            self.close_current_connection()

        return citation_id

    def _exists_cover(self, cover, solution_id, close=True):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM cover WHERE source=:cover_source AND description=:cover_description "
            "AND solution_id=:solution_id",
            {
                "cover_source": cover["source"],
                "cover_description": cover["description"],
                "solution_id": solution_id,
            },
        ).fetchone()

        if close:
            self.close_current_connection()

        return r["cover_id"] if r else None

    def _insert_cover(self, cover, solution_id, close=True):
        cover_id = self.next_id("cover")

        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO cover values (?, ?, ?, ?)",
            (cover_id, solution_id, cover["source"], cover["description"]),
        )

        if close:
            self.close_current_connection()

        return cover_id

    def _exists_documentation(self, documentation, solution_id, close=True):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM main.documentation WHERE documentation=:documentation "
            "AND solution_id=:solution_id",
            {
                "documentation": documentation,
                "solution_id": solution_id,
            },
        ).fetchone()

        if close:
            self.close_current_connection()

        return r["documentation_id"] if r else None

    def _insert_documentation(self, documentation, solution_id, close=True):
        documentation_id = self.next_id("documentation")
        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO documentation values (?, ?, ?)",
            (documentation_id, solution_id, documentation),
        )

        if close:
            self.close_current_connection()

        return documentation_id

    def get_solution(self, solution_id, close=True) -> Optional[dict]:
        module_logger().debug('Get solution by id: "%s"...' % solution_id)

        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM solution WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id,
            },
        ).fetchone()
        solution = None
        if r:
            solution = dict(r)
            self._append_metadata_to_solution_dict(solution)

        if close:
            self.close_current_connection()

        return solution

    def get_solution_by_coordinates(
        self, coordinates: ICoordinates, close=True
    ) -> Optional[dict]:
        module_logger().debug('Get solution by coordinates: "%s"...' % str(coordinates))

        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT s.* FROM solution s "
            'WHERE s."group"=:group AND s.name=:name AND s.version=:version',
            {
                "group": coordinates.group(),
                "name": coordinates.name(),
                "version": coordinates.version(),
            },
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
        solution["solution_creators"] = self._get_authors_by_solution(solution_id)
        solution["covers"] = self._get_covers_by_solution(solution_id)
        solution["documentation"] = self._get_documentation_by_solution(solution_id)
        solution["args"] = self._get_arguments_by_solution(solution_id)
        solution["cite"] = self._get_citations_by_solution(solution_id)
        solution["tags"] = self._get_tags_by_solution(solution_id)
        solution["custom"] = self._get_custom_by_solution(solution_id)

    def get_solution_by_doi(self, doi, close=True) -> Optional[dict]:
        module_logger().debug('Get solution by doi: "%s"...' % doi)

        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM solution WHERE doi=:doi_value",
            {
                "doi_value": doi,
            },
        ).fetchone()

        solution = None
        if r:
            solution = dict(r)

        if close:
            self.close_current_connection()

        return solution

    def get_all_solution_versions(
        self, group, name, close=True
    ) -> Optional[List[dict]]:
        module_logger().debug(
            'Get solution by group and name: "%s:%s"...' % (group, name)
        )

        cursor = self.get_cursor()
        r = cursor.execute(
            'SELECT * FROM solution WHERE "group"=:group_value AND name=:name_value ORDER BY version DESC',
            {
                "group_value": group,
                "name_value": name,
            },
        ).fetchall()

        solutions = []
        if r:
            for solution in r:
                solutions.append(dict(solution))

        if close:
            self.close_current_connection()

        return solutions

    def _update_solution(
        self, coordinates: ICoordinates, solution_attrs: dict, close=True
    ) -> None:
        try:
            # it is easier to delete and insert again instead of updating all connection-tables
            solution_dict = self.get_solution_by_coordinates(coordinates, close=False)
            if solution_dict:
                self.remove_solution(solution_dict["solution_id"])
            else:
                raise RuntimeError(
                    'Cannot update solution "%s"! Does not exist!' % str(coordinates)
                )

            self._insert_solution(solution_attrs, close=False)

            self.save()
        finally:
            if close:
                self.close_current_connection()

    def remove_solution(self, solution_id, close=True):
        cursor = self.get_cursor()

        cursor.execute(
            "DELETE FROM cover WHERE solution_id=:solution_id",
            {"solution_id": solution_id},
        )
        cursor.execute(
            "DELETE FROM documentation WHERE solution_id=:solution_id",
            {"solution_id": solution_id},
        )

        cursor.execute(
            "DELETE FROM solution_tag WHERE solution_id=:solution_id",
            {"solution_id": solution_id},
        )

        cursor.execute(
            "DELETE FROM solution_author WHERE solution_id=:solution_id",
            {"solution_id": solution_id},
        )

        cursor.execute(
            "DELETE FROM solution_citation WHERE solution_id=:solution_id",
            {"solution_id": solution_id},
        )

        cursor.execute(
            "DELETE FROM solution_argument WHERE solution_id=:solution_id",
            {"solution_id": solution_id},
        )

        cursor.execute(
            "DELETE FROM solution_custom WHERE solution_id=:solution_id",
            {"solution_id": solution_id},
        )

        cursor.execute(
            "DELETE FROM tag "
            "WHERE NOT EXISTS (SELECT st.tag_id FROM solution_tag st "
            "WHERE tag.tag_id = st.tag_id)"
        )

        cursor.execute(
            "DELETE FROM argument "
            "WHERE NOT EXISTS (SELECT sa.argument_id FROM solution_argument sa "
            "WHERE argument.argument_id = sa.argument_id)"
        )

        cursor.execute(
            "DELETE FROM citation "
            "WHERE NOT EXISTS (SELECT sc.citation_id FROM solution_citation sc "
            "WHERE citation.citation_id = sc.citation_id)"
        )

        cursor.execute(
            "DELETE FROM author "
            "WHERE NOT EXISTS (SELECT sa.author_id FROM solution_author sa "
            "WHERE author.author_id = sa.author_id)"
        )

        cursor.execute(
            "DELETE FROM custom "
            "WHERE NOT EXISTS (SELECT sa.custom_id FROM solution_custom sa "
            "WHERE custom.custom_id = sa.custom_id)"
        )

        cursor.execute(
            "DELETE FROM solution WHERE solution_id=:solution_id",
            {"solution_id": solution_id},
        )

        self.save()

        if close:
            self.close_current_connection()

    def remove_solution_by_group_name_version(
        self, coordinates: ICoordinates, close=True
    ):
        solution_dict = self.get_solution_by_coordinates(coordinates, close=close)
        if solution_dict:
            self.remove_solution(solution_dict["solution_id"])
            return solution_dict
        return None

    # ### catalog_features ###

    def update(self, coordinates: ICoordinates, solution_attrs: dict, close=True):
        if self.get_solution_by_coordinates(coordinates, close=False):
            module_logger().debug("Update solution...")
            self._update_solution(coordinates, solution_attrs, close=close)
        else:
            module_logger().debug("Insert solution...")
            self._insert_solution(solution_attrs, close=close)

    def save(self):
        module_logger().debug("Saving index...")
        self.get_connection().commit()

    def export(self, path, export_format="JSON", close=True):
        module_logger().debug("Export index...")

        cursor = self.get_cursor()
        r = cursor.execute("SELECT * FROM solution").fetchall()

        if export_format == "JSON":
            json_dumps_list = []
            for solution in r:
                solution = dict(solution)
                self._append_metadata_to_solution_dict(solution)
                json_dumps_list.append(serialize_json(solution))

            write_dict_to_json(path, json_dumps_list)
        else:
            raise NotImplementedError('Unsupported format "%s"' % export_format)

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
            {"solution_id": solution_id},
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
            {"solution_id": solution_id},
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
            {"solution_id": solution_id},
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
            {"solution_id": solution_id},
        ).fetchall()

        res = []
        for row in r:
            row = dict(row)
            argument = {"name": row["name"], "type": row["type"]}
            if "description" in row and row["description"] is not None:
                argument["description"] = row["description"]
            if "required" in row and row["required"] is not None:
                argument["required"] = bool(row["required"])
            if "default_value" in row and row["default_value"] is not None:
                argument["default"] = row["default_value"]
            res.append(argument)

        if close:
            self.close_current_connection()

        return res

    def _get_custom_by_solution(self, solution_id, close=True):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT a.* FROM custom a "
            "JOIN solution_custom sa ON sa.custom_id = a.custom_id "
            "WHERE sa.solution_id=:solution_id",
            {"solution_id": solution_id},
        ).fetchall()

        res = {}
        for row in r:
            dict_row = dict(row)
            res[row["custom_key"]] = row["custom_value"]

        if close:
            self.close_current_connection()

        return res

    def _get_covers_by_solution(self, solution_id, close=True):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT c.* FROM cover c " "WHERE c.solution_id=:solution_id",
            {"solution_id": solution_id},
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
            "SELECT d.* FROM documentation d " "WHERE d.solution_id=:solution_id",
            {"solution_id": solution_id},
        ).fetchall()

        res = []
        for row in r:
            res.append(row["documentation"])

        if close:
            self.close_current_connection()

        return res

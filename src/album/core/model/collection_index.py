import pkgutil
from datetime import datetime
from typing import Optional, List

from album.core.api.model.collection_index import ICollectionIndex
from album.core.model.catalog_index import CatalogIndex
from album.core.model.database import Database
from album.core.utils.operations.file_operations import get_dict_entry
from album.core.utils.operations.solution_operations import get_solution_hash
from album.runner.core.api.model.coordinates import ICoordinates
from album.core.model.default_values import DefaultValues


class CollectionIndex(ICollectionIndex, Database):

    class CollectionSolution(ICollectionIndex.ICollectionSolution):
        def __init__(self, setup: dict = None, internal: dict = None):
            if setup:
                self._setup = setup
            else:
                self._setup = {}
            if internal:
                self._internal = internal
            else:
                self._internal = {}

        def __eq__(self, other) -> bool:
            return other.setup() == self._setup and other.internal() == self._internal

        def setup(self) -> dict:
            return self._setup

        def internal(self) -> dict:
            return self._internal

    def __init__(self, name, path):
        self.name = name
        super().__init__(path)

    def create(self):
        data = pkgutil.get_data("album.core.schema", "catalog_collection_schema.sql")
        cursor = self.get_cursor()
        cursor.executescript(data.decode("utf-8"))
        self.update_name_version(self.name, DefaultValues.catalog_collection_db_version.value, close=False)

        self.close_current_connection()

    def update_name_version(self, name, version, close=True):
        curr_name = self.get_name(close=False)

        cursor = self.get_cursor()
        if curr_name:
            cursor.execute(
                "UPDATE catalog_collection SET name=:name, version=:version WHERE name_id=:name_id",
                {"name_id": 1, "name": name, "version": version},
            )
        else:
            cursor.execute(
                "INSERT INTO catalog_collection values (?, ?, ?)", (1, name, version)
            )

        if close:
            self.close_current_connection()

    def get_name(self, close=True):
        cursor = self.get_cursor()

        r = cursor.execute("SELECT * FROM catalog_collection").fetchone()

        cur_name = r["name"] if r else None

        if close:
            self.close_current_connection()

        return cur_name

    def get_version(self, close=True):
        cursor = self.get_cursor()

        r = cursor.execute("SELECT * FROM catalog_collection").fetchone()

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

    def insert_catalog(
        self, name, src, path, deletable, branch_name, catalog_type, close=True
    ):
        next_id = self.next_id("catalog")
        cursor = self.get_cursor()

        cursor.execute(
            "INSERT INTO catalog VALUES (?, ?, ?, ?, ?, ?, ?)",
            (next_id, name, src, path, branch_name, catalog_type, deletable),
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
            },
        ).fetchone()

        catalog = None
        if r:
            catalog = dict(r)

        if close:
            self.close_current_connection()

        return catalog

    def get_catalog_by_name(self, catalog_name: str, close=True):
        cursor = self.get_cursor()

        r = cursor.execute(
            "SELECT * FROM catalog WHERE name=:catalog_name",
            {
                "catalog_name": catalog_name,
            },
        ).fetchone()

        catalog = None
        if r:
            catalog = dict(r)

        if close:
            self.close_current_connection()

        return catalog

    def get_catalog_by_path(self, catalog_path: str, close=True):
        cursor = self.get_cursor()

        r = cursor.execute(
            "SELECT * FROM catalog WHERE path=:catalog_path",
            {
                "catalog_path": catalog_path,
            },
        ).fetchone()

        catalog = None
        if r:
            catalog = dict(r)

        if close:
            self.close_current_connection()

        return catalog

    def get_catalog_by_src(self, catalog_src: str, close=True):
        cursor = self.get_cursor()

        r = cursor.execute(
            "SELECT * FROM catalog WHERE src=:catalog_src",
            {
                "catalog_src": catalog_src,
            },
        ).fetchone()

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

    def remove_catalog(self, catalog_id, close=True):
        cursor = self.get_cursor()
        cursor.execute(
            "DELETE FROM collection " "WHERE catalog_id=:catalog_id",
            {"catalog_id": catalog_id},
        )
        cursor.execute(
            "DELETE FROM collection_tag " "WHERE catalog_id=:catalog_id",
            {"catalog_id": catalog_id},
        )
        cursor.execute(
            "DELETE FROM tag " "WHERE catalog_id=:catalog_id",
            {"catalog_id": catalog_id},
        )
        cursor.execute(
            "DELETE FROM collection_author " "WHERE catalog_id=:catalog_id",
            {"catalog_id": catalog_id},
        )
        cursor.execute(
            "DELETE FROM author " "WHERE catalog_id=:catalog_id",
            {"catalog_id": catalog_id},
        )
        cursor.execute(
            "DELETE FROM collection_citation " "WHERE catalog_id=:catalog_id",
            {"catalog_id": catalog_id},
        )
        cursor.execute(
            "DELETE FROM citation " "WHERE catalog_id=:catalog_id",
            {"catalog_id": catalog_id},
        )
        cursor.execute(
            "DELETE FROM collection_argument " "WHERE catalog_id=:catalog_id",
            {"catalog_id": catalog_id},
        )
        cursor.execute(
            "DELETE FROM argument " "WHERE catalog_id=:catalog_id",
            {"catalog_id": catalog_id},
        )
        cursor.execute(
            "DELETE FROM collection_custom " "WHERE catalog_id=:catalog_id",
            {"catalog_id": catalog_id},
        )
        cursor.execute(
            "DELETE FROM custom " "WHERE catalog_id=:catalog_id",
            {"catalog_id": catalog_id},
        )
        cursor.execute(
            "DELETE FROM cover " "WHERE catalog_id=:catalog_id",
            {"catalog_id": catalog_id},
        )
        cursor.execute(
            "DELETE FROM documentation " "WHERE catalog_id=:catalog_id",
            {"catalog_id": catalog_id},
        )
        cursor.execute(
            "DELETE FROM collection_collection " "WHERE catalog_id_parent=:catalog_id",
            {"catalog_id": catalog_id},
        )
        cursor.execute(
            "DELETE FROM collection_collection " "WHERE catalog_id_child=:catalog_id",
            {"catalog_id": catalog_id},
        )
        cursor.execute(
            "DELETE FROM catalog " "WHERE catalog_id=:catalog_id",
            {"catalog_id": catalog_id},
        )

        if close:
            self.close_current_connection()

    # ### collection ###

    def insert_solution(self, catalog_id, solution_attrs, close=True):
        collection_id = self.next_id("collection")
        hash_val = get_dict_entry(solution_attrs, "hash", allow_none=True)

        # there must be a hash value
        if not hash_val:
            hash_val = get_solution_hash(
                solution_attrs, CatalogIndex.get_solution_column_keys()
            )

        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO collection VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? ,? ,?, ?, ? ,?, ?, ?, ?)",
            (
                collection_id,
                get_dict_entry(solution_attrs, "solution_id"),
                solution_attrs["group"],
                solution_attrs["name"],
                get_dict_entry(solution_attrs, "title"),
                solution_attrs["version"],
                get_dict_entry(solution_attrs, "timestamp"),
                get_dict_entry(solution_attrs, "description"),
                get_dict_entry(solution_attrs, "doi"),
                get_dict_entry(solution_attrs, "license"),
                get_dict_entry(solution_attrs, "album_version"),
                get_dict_entry(solution_attrs, "album_api_version"),
                get_dict_entry(solution_attrs, "changelog"),
                get_dict_entry(solution_attrs, "acknowledgement"),
                hash_val,
                None,  # when installed?
                None,  # last executed
                0,  # installation unfinished
                0,  # installed
                catalog_id,
            ),
        )

        if "solution_creators" in solution_attrs:
            for author in solution_attrs["solution_creators"]:
                author_id = self._exists_author(author, catalog_id, close=False)
                if not author_id:
                    author_id = self._insert_author(author, catalog_id, close=False)
                self._insert_collection_author(
                    collection_id, author_id, catalog_id, close=False
                )

        if "tags" in solution_attrs:
            for tag in solution_attrs["tags"]:
                tag_id = self._exists_tag(tag, catalog_id, close=False)
                if not tag_id:
                    tag_id = self._insert_tag(tag, catalog_id, close=False)
                self._insert_collection_tag(
                    collection_id, tag_id, catalog_id, close=False
                )

        if "cite" in solution_attrs:
            for citation in solution_attrs["cite"]:
                citation_id = self._exists_citation(citation, catalog_id, close=False)
                if not citation_id:
                    citation_id = self._insert_citation(
                        citation, catalog_id, close=False
                    )
                self._insert_collection_citation(
                    collection_id, citation_id, catalog_id, close=False
                )

        if "args" in solution_attrs:
            for argument in solution_attrs["args"]:
                argument_id = self._exists_argument(argument, catalog_id)
                if not argument_id:
                    argument_id = self._insert_argument(
                        argument, catalog_id, close=False
                    )
                self._insert_collection_argument(
                    collection_id, argument_id, catalog_id, close=False
                )

        if "covers" in solution_attrs:
            for cover in solution_attrs["covers"]:
                if not self._exists_cover(cover, catalog_id, collection_id):
                    self._insert_cover(cover, catalog_id, collection_id, close=False)

        if "documentation" in solution_attrs:
            for documentation in solution_attrs["documentation"]:
                if not self._exists_documentation(
                    documentation, catalog_id, collection_id, close=False
                ):
                    self._insert_documentation(
                        documentation, catalog_id, collection_id, close=False
                    )

        if "custom" in solution_attrs:
            for custom in solution_attrs["custom"]:
                custom_value = solution_attrs["custom"][custom]
                custom_id = self._exists_custom(custom, custom_value, catalog_id)
                if not custom_id:
                    custom_id = self._insert_custom(
                        custom, custom_value, catalog_id, close=False
                    )
                self._insert_collection_custom(
                    collection_id, custom_id, catalog_id, close=False
                )

        if close:
            self.close_current_connection()

        return collection_id

    def _insert_collection_argument(
        self, collection_id, argument_id, catalog_id, close=True
    ):
        collection_solution_argument_id = self.next_id("collection_argument")

        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO collection_argument values (?, ?, ?, ?)",
            (collection_solution_argument_id, collection_id, argument_id, catalog_id),
        )

        if close:
            self.close_current_connection()

        return collection_solution_argument_id

    def _insert_collection_custom(
        self, collection_id, custom_id, catalog_id, close=True
    ):
        collection_solution_custom_id = self.next_id("collection_custom")

        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO collection_custom values (?, ?, ?, ?)",
            (collection_solution_custom_id, collection_id, custom_id, catalog_id),
        )

        if close:
            self.close_current_connection()

        return collection_solution_custom_id

    def _insert_collection_citation(
        self, collection_id, citation_id, catalog_id, close=True
    ):
        collection_solution_citation_id = self.next_id("collection_citation")

        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO collection_citation values (?, ?, ?, ?)",
            (collection_solution_citation_id, collection_id, citation_id, catalog_id),
        )

        if close:
            self.close_current_connection()

        return collection_solution_citation_id

    def _insert_collection_tag(self, collection_id, tag_id, catalog_id, close=True):
        collection_solution_tag_id = self.next_id("collection_tag")

        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO collection_tag values (?, ?, ?, ?)",
            (collection_solution_tag_id, collection_id, tag_id, catalog_id),
        )

        if close:
            self.close_current_connection()

        return collection_solution_tag_id

    def _insert_collection_author(
        self, collection_id, author_id, catalog_id, close=True
    ):
        collection_author_id = self.next_id("collection_author")

        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO collection_author values (?, ?, ?, ?)",
            (collection_author_id, collection_id, author_id, catalog_id),
        )

        if close:
            self.close_current_connection()

        return collection_author_id

    def _exists_author(self, author_name, catalog_id, close=True):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM author WHERE name=:author_name AND catalog_id=:catalog_id",
            {"author_name": author_name, "catalog_id": catalog_id},
        ).fetchone()

        if close:
            self.close_current_connection()

        return r["author_id"] if r else None

    def _insert_author(self, author, catalog_id, close=True):
        author_id = self.next_id("author")

        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO author values (?, ?, ?)", (author_id, catalog_id, author)
        )

        if close:
            self.close_current_connection()

        return author_id

    def _exists_tag(self, tag_name, catalog_id, close=True):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM tag WHERE name=:tag_name AND catalog_id=:catalog_id",
            {"tag_name": tag_name, "catalog_id": catalog_id},
        ).fetchone()

        if close:
            self.close_current_connection()

        return r["tag_id"] if r else None

    def _insert_tag(self, tag, catalog_id, close=True):
        tag_id = self.next_id("tag")
        cursor = self.get_cursor()

        cursor.execute(
            "INSERT INTO tag values (?, ?, ?, ?)", (tag_id, catalog_id, tag, "manual")
        )

        if close:
            self.close_current_connection()

        return tag_id

    def _exists_argument(self, argument, catalog_id, close=True):
        cursor = self.get_cursor()

        exc_str = (
            "SELECT * FROM argument WHERE name=:argument_name AND description=:argument_description "
            "AND catalog_id=:catalog_id "
        )
        exc_val = {
            "argument_name": argument["name"],
            "argument_description": argument["description"],
            "catalog_id": catalog_id,
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

    def _exists_custom(self, custom_key, custom_value, catalog_id, close=True):
        cursor = self.get_cursor()

        exc_str = (
            "SELECT * FROM custom WHERE custom_key=:custom_key AND custom_value=:custom_value "
            "AND catalog_id=:catalog_id "
        )
        exc_val = {
            "custom_key": custom_key,
            "custom_value": custom_value,
            "catalog_id": catalog_id,
        }

        r = cursor.execute(exc_str, exc_val).fetchone()

        if close:
            self.close_current_connection()

        return r["custom_id"] if r else None

    def _insert_argument(self, argument, catalog_id, close=True):
        argument_id = self.next_id("argument")
        cursor = self.get_cursor()

        cursor.execute(
            "INSERT INTO argument values (?, ?, ?, ?, ?, ?, ?)",
            (
                argument_id,
                catalog_id,
                argument["name"],
                get_dict_entry(argument, "type"),
                argument["description"],
                get_dict_entry(argument, "default"),
                get_dict_entry(argument, "required"),
            ),
        )

        if close:
            self.close_current_connection()

        return argument_id

    def _insert_custom(self, custom_key, custom_value, catalog_id, close=True):
        custom_id = self.next_id("custom")
        cursor = self.get_cursor()

        cursor.execute(
            "INSERT INTO custom values (?, ?, ?, ?)",
            (custom_id, catalog_id, custom_key, custom_value),
        )

        if close:
            self.close_current_connection()

        return custom_id

    def _exists_citation(self, citation, catalog_id, close=True):
        cursor = self.get_cursor()

        exc_str = "SELECT * FROM citation WHERE text=:citation_text AND catalog_id=:catalog_id "
        exc_val = {"citation_text": citation["text"], "catalog_id": catalog_id}
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

    def _insert_citation(self, citation, catalog_id, close=True):
        citation_id = self.next_id("citation")

        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO citation values (?, ?, ?, ?, ?)",
            (
                citation_id,
                catalog_id,
                citation["text"],
                get_dict_entry(citation, "doi"),
                get_dict_entry(citation, "url"),
            ),
        )

        if close:
            self.close_current_connection()

        return citation_id

    def _exists_cover(self, cover, catalog_id, collection_id, close=True):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM cover WHERE source=:cover_source AND description=:cover_description "
            "AND catalog_id=:catalog_id AND collection_id=:collection_id",
            {
                "cover_source": cover["source"],
                "cover_description": cover["description"],
                "catalog_id": catalog_id,
                "collection_id": collection_id,
            },
        ).fetchone()

        if close:
            self.close_current_connection()

        return r["cover_id"] if r else None

    def _insert_cover(self, cover, catalog_id, collection_id, close=True):
        cover_id = self.next_id("cover")

        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO cover values (?, ?, ?, ?, ?)",
            (
                cover_id,
                collection_id,
                catalog_id,
                cover["source"],
                cover["description"],
            ),
        )

        if close:
            self.close_current_connection()

        return cover_id

    def _exists_documentation(
        self, documentation, catalog_id, collection_id, close=True
    ):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM main.documentation WHERE documentation=:documentation "
            "AND catalog_id=:catalog_id AND collection_id=:collection_id",
            {
                "documentation": documentation,
                "catalog_id": catalog_id,
                "collection_id": collection_id,
            },
        ).fetchone()

        if close:
            self.close_current_connection()

        return r["documentation_id"] if r else None

    def _insert_documentation(
        self, documentation, catalog_id, collection_id, close=True
    ):
        documentation_id = self.next_id("documentation")
        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO documentation values (?, ?, ?, ?)",
            (documentation_id, collection_id, catalog_id, documentation),
        )

        if close:
            self.close_current_connection()

        return documentation_id

    def insert_collection_collection(
        self,
        collection_id_parent,
        collection_id_child,
        catalog_id_parent,
        catalog_id_child,
        close=True,
    ):

        if not self._exists_collection_collection(
            collection_id_parent,
            collection_id_child,
            catalog_id_parent,
            catalog_id_child,
            close=False,
        ):

            solution_solution_id = self.next_id("collection_collection")

            cursor = self.get_cursor()
            cursor.execute(
                "INSERT INTO collection_collection values (?, ?, ?, ?, ?)",
                (
                    solution_solution_id,
                    collection_id_parent,
                    collection_id_child,
                    catalog_id_parent,
                    catalog_id_child,
                ),
            )
        if close:
            self.close_current_connection()

    def _exists_collection_collection(
        self,
        collection_id_parent,
        collection_id_child,
        catalog_id_parent,
        catalog_id_child,
        close=True,
    ):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM collection_collection WHERE collection_id_parent=:collection_id_parent "
            "AND collection_id_child=:collection_id_child AND catalog_id_parent=:catalog_id_parent "
            "AND catalog_id_child=:catalog_id_child",
            {
                "collection_id_parent": collection_id_parent,
                "collection_id_child": collection_id_child,
                "catalog_id_parent": catalog_id_parent,
                "catalog_id_child": catalog_id_child,
            },
        ).fetchone()

        if close:
            self.close_current_connection()

        return r["collection_collection_id"] if r else None

    def remove_parent(self, collection_id, close=True):
        cursor = self.get_cursor()
        cursor.execute(
            "DELETE FROM collection_collection WHERE collection_id_child=:collection_id",
            {"collection_id": collection_id},
        )

        if close:
            self.close_current_connection()

    def _get_children_of_solution(self, collection_id, close=True):
        child_solutions = []
        cursor = self.get_cursor()

        r = cursor.execute(
            "SELECT css.* FROM collection_collection css "
            "JOIN collection c ON c.collection_id = css.collection_id_parent "
            "WHERE c.collection_id=:collection_id",
            {"collection_id": collection_id},
        ).fetchall()

        for row in r:
            child_solutions.append(
                dict(row)
            )  # do not resolve get this solution here: recursion!

        if close:
            self.close_current_connection()

        return child_solutions

    def get_parent_of_solution(
        self, collection_id, close=True
    ) -> Optional[CollectionSolution]:
        parent_solution = None
        cursor = self.get_cursor()

        r = cursor.execute(
            "SELECT css.* FROM collection_collection css "
            "JOIN collection c ON c.collection_id = css.collection_id_child "
            "WHERE c.collection_id=:collection_id",
            {"collection_id": collection_id},
        ).fetchall()

        if len(r) > 1:
            raise KeyError(
                "Database error. Solution with id %s has several parents!"
                % str(collection_id)
            )

        for row in r:
            parent_solution = self.get_solution_by_collection_id(
                row["collection_id_parent"], close=False
            )

        if close:
            self.close_current_connection()

        return parent_solution

    def get_all_solutions(self, close=True) -> List[CollectionSolution]:
        solutions_list = []
        cursor = self.get_cursor()
        for row in cursor.execute("SELECT * FROM collection").fetchall():
            solution = self._process_solution_row(dict(row), close=False)
            solutions_list.append(solution)

        if close:
            self.close_current_connection()

        return solutions_list

    def get_all_installed_solutions_by_catalog(self, catalog_id, close=True):
        solutions_list = []

        cursor = self.get_cursor()
        for row in cursor.execute(
            "SELECT * FROM collection WHERE installed=:installed AND catalog_id=:catalog_id",
            {"installed": 1, "catalog_id": catalog_id},
        ).fetchall():
            solution = self._process_solution_row(dict(row), close=False)
            solutions_list.append(solution)

        if close:
            self.close_current_connection()

        return solutions_list

    def _process_solution_row(self, solution_dict, close=True) -> CollectionSolution:
        setup = {}
        internal = {}
        collection_id = solution_dict["collection_id"]
        for key in CatalogIndex.get_solution_column_keys():
            setup[key] = solution_dict[key]
        for key in solution_dict.keys():
            if key not in setup:
                internal[key] = solution_dict[key]
        setup["solution_creators"] = self._get_authors_by_solution(
            collection_id, close=False
        )
        setup["tags"] = self._get_tags_by_solution(collection_id, close=False)
        setup["cite"] = self._get_citations_by_solution(collection_id, close=False)
        setup["args"] = self._get_arguments_by_solution(collection_id, close=False)
        setup["covers"] = self._get_covers_by_solution(collection_id, close=False)
        setup["documentation"] = self._get_documentation_by_solution(
            collection_id, close=False
        )
        setup["custom"] = self._get_custom_by_solution(collection_id, close=False)
        internal["children"] = self._get_children_of_solution(
            collection_id, close=False
        )
        internal["parent"] = self.get_parent_of_solution(collection_id, close=close)
        return CollectionIndex.CollectionSolution(setup, internal)

    def _get_authors_by_solution(self, collection_id, close=True):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT a.* FROM author a "
            "JOIN collection_author sa ON sa.author_id = a.author_id "
            "WHERE sa.collection_id=:collection_id",
            {"collection_id": collection_id},
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
            "SELECT a.* FROM argument a "
            "JOIN collection_argument sa ON sa.argument_id = a.argument_id "
            "WHERE sa.collection_id=:collection_id",
            {"collection_id": collection_id},
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

    def _get_custom_by_solution(self, collection_id, close=True):
        cursor = self.get_cursor()

        r = cursor.execute(
            "SELECT a.* FROM custom a "
            "JOIN collection_custom sa ON sa.custom_id = a.custom_id "
            "WHERE sa.collection_id=:collection_id",
            {"collection_id": collection_id},
        ).fetchall()

        res = {}
        for row in r:
            res[row["custom_key"]] = row["custom_value"]

        if close:
            self.close_current_connection()

        return res

    def _get_tags_by_solution(self, collection_id, close=True):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT t.* FROM tag t "
            "JOIN collection_tag st ON st.tag_id = t.tag_id "
            "WHERE st.collection_id=:collection_id",
            {"collection_id": collection_id},
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
            "SELECT c.* FROM citation c "
            "JOIN collection_citation sc ON sc.citation_id = c.citation_id "
            "WHERE sc.collection_id=:collection_id",
            {"collection_id": collection_id},
        ).fetchall()

        res = []
        for row in r:
            citation = {"text": row["text"]}
            if row["doi"]:
                citation["doi"] = row["doi"]
            if row["url"]:
                citation["url"] = row["url"]
            res.append(citation)

        if close:
            self.close_current_connection()

        return res

    def _get_covers_by_solution(self, collection_id, close=True):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT c.* FROM cover c " "WHERE c.collection_id=:collection_id",
            {"collection_id": collection_id},
        ).fetchall()

        res = []
        for row in r:
            cover = {"description": row["description"], "source": row["source"]}
            res.append(cover)

        if close:
            self.close_current_connection()

        return res

    def _get_documentation_by_solution(self, collection_id, close=True):
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT d.* FROM documentation d " "WHERE d.collection_id=:collection_id",
            {"collection_id": collection_id},
        ).fetchall()

        res = []
        for row in r:
            res.append(row["documentation"])

        if close:
            self.close_current_connection()

        return res

    def get_solutions_by_catalog(
        self, catalog_id, close=True
    ) -> List[CollectionSolution]:
        catalog_solutions = []

        cursor = self.get_cursor()
        for row in cursor.execute(
            "SELECT c.* FROM collection c " "WHERE c.catalog_id=:catalog_id",
            {"catalog_id": catalog_id},
        ).fetchall():
            solution = self._process_solution_row(dict(row), close=False)
            catalog_solutions.append(solution)

        if close:
            self.close_current_connection()

        return catalog_solutions

    def get_solution_by_hash(
        self, hash_value, close=True
    ) -> Optional[CollectionSolution]:
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM collection WHERE hash=:hash_value",
            {"hash_value": hash_value},
        ).fetchone()

        solution = None
        if r:
            solution = self._process_solution_row(dict(r), close=False)

        if close:
            self.close_current_connection()

        return solution

    def get_solution_by_collection_id(
        self, collection_id, close=True
    ) -> Optional[CollectionSolution]:
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM collection WHERE collection_id=:collection_id",
            {
                "collection_id": collection_id,
            },
        ).fetchone()

        solution = None
        if r:
            solution = self._process_solution_row(dict(r), close=False)

        if close:
            self.close_current_connection()

        return solution

    def get_solution_by_doi(self, doi, close=True) -> Optional[CollectionSolution]:
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM collection WHERE doi=:doi",
            {
                "doi": doi,
            },
        ).fetchone()

        solution = None
        if r:
            solution = self._process_solution_row(dict(r), close=False)

        if close:
            self.close_current_connection()

        return solution

    def get_solution_by_catalog_grp_name_version(
        self, catalog_id, coordinates: ICoordinates, close=True
    ) -> Optional[CollectionSolution]:
        cursor = self.get_cursor()
        r = cursor.execute(
            "SELECT * FROM collection "
            'WHERE catalog_id=:catalog_id AND "group"=:group AND name=:name AND version=:version',
            {
                "catalog_id": catalog_id,
                "group": coordinates.group(),
                "name": coordinates.name(),
                "version": coordinates.version(),
            },
        ).fetchall()

        if len(r) > 1:
            raise KeyError(
                "Database error. Please reinstall the solution %s from catalog %s !"
                % (coordinates.group(), catalog_id)
            )

        solution = None
        for row in r:
            solution = self._process_solution_row(dict(row), close=False)

        if close:
            self.close_current_connection()

        return solution

    def get_solutions_by_grp_name_version(
        self, coordinates: ICoordinates, close=True
    ) -> List[CollectionSolution]:
        solutions_list = []

        cursor = self.get_cursor()
        for row in cursor.execute(
            'SELECT * FROM collection WHERE "group"=:group AND name=:name AND version=:version',
            {
                "group": coordinates.group(),
                "name": coordinates.name(),
                "version": coordinates.version(),
            },
        ).fetchall():
            solution = self._process_solution_row(dict(row), close=False)
            solutions_list.append(solution)

        if close:
            self.close_current_connection()

        return solutions_list

    def get_solutions_by_grp_name(
        self, group: str, name: str, close=True
    ) -> List[CollectionSolution]:
        solutions_list = []

        cursor = self.get_cursor()
        for row in cursor.execute(
            'SELECT * FROM collection WHERE "group"=:group AND name=:name',
            {"group": group, "name": name},
        ).fetchall():
            solution = self._process_solution_row(dict(row), close=False)
            solutions_list.append(solution)

        if close:
            self.close_current_connection()

        return solutions_list

    def get_solutions_by_name_version(
        self, name: str, version: str, close=True
    ) -> List[CollectionSolution]:
        solutions_list = []

        cursor = self.get_cursor()
        for row in cursor.execute(
            "SELECT * FROM collection WHERE name=:name AND version=:version",
            {
                "name": name,
                "version": version,
            },
        ).fetchall():
            solution = self._process_solution_row(dict(row), close=False)
            solutions_list.append(solution)

        if close:
            self.close_current_connection()

        return solutions_list

    def get_solutions_by_name(self, name: str, close=True) -> List[CollectionSolution]:
        solutions_list = []

        cursor = self.get_cursor()
        for row in cursor.execute(
            "SELECT * FROM collection WHERE name=:name", {"name": name}
        ).fetchall():
            solution = self._process_solution_row(dict(row), close=False)
            solutions_list.append(solution)

        if close:
            self.close_current_connection()

        return solutions_list

    def get_recently_installed_solutions(self, close=True) -> List[CollectionSolution]:
        solutions_list = []

        cursor = self.get_cursor()
        for row in cursor.execute(
            "SELECT * FROM collection WHERE installed=:installed ORDER BY install_date ",
            {"installed": 1},
        ).fetchall():
            solution = self._process_solution_row(dict(row), close=False)
            solutions_list.append(solution)

        if close:
            self.close_current_connection()

        return solutions_list

    def get_recently_launched_solutions(self, close=True) -> List[CollectionSolution]:
        solutions_list = []

        cursor = self.get_cursor()
        for row in cursor.execute(
            "SELECT * FROM collection WHERE last_execution IS NOT NULL ORDER BY last_execution"
        ).fetchall():
            solution = self._process_solution_row(dict(row), close=False)
            solutions_list.append(solution)

        if close:
            self.close_current_connection()

        return solutions_list

    def get_unfinished_installation_solutions(self, close=True):
        solutions_list = []

        cursor = self.get_cursor()
        for row in cursor.execute(
            "SELECT * FROM collection WHERE installation_unfinished=:installation_unfinished ",
            {"installation_unfinished": 1},
        ).fetchall():
            solution = self._process_solution_row(dict(row), close=False)
            solutions_list.append(solution)

        if close:
            self.close_current_connection()

        return solutions_list

    def update_solution(
        self,
        catalog_id,
        coordinates: ICoordinates,
        solution_attrs: dict,
        supported_attrs: list,
        close=True,
    ):
        exec_str = "UPDATE collection SET last_execution=:cur_date"
        exec_args = {
            "cur_date": datetime.now().isoformat(),
            "catalog_id": catalog_id,
            "group": coordinates.group(),
            "name": coordinates.name(),
            "version": coordinates.version(),
        }

        for key in supported_attrs:
            if key in solution_attrs:
                col = self._as_db_col(key)
                exec_str += f", {col}=:{key}"
                exec_args[key] = get_dict_entry(solution_attrs, key)

        exec_str += ' WHERE catalog_id=:catalog_id AND "group"=:group AND name=:name AND version=:version'

        cursor = self.get_cursor()
        cursor.execute(exec_str, exec_args)

        if close:
            self.close_current_connection()

    def add_or_replace_solution(
        self, catalog_id, coordinates: ICoordinates, solution_attrs, close=True
    ):
        solution = self.get_solution_by_catalog_grp_name_version(
            catalog_id, coordinates, close=False
        )
        if solution:
            self.remove_solution(catalog_id, coordinates, close=False)
        self.insert_solution(catalog_id, solution_attrs, close=close)

    def remove_solution(self, catalog_id, coordinates: ICoordinates, close=True):
        solution = self.get_solution_by_catalog_grp_name_version(
            catalog_id, coordinates, close=False
        )
        if not solution:
            return
        collection_id = solution.internal()["collection_id"]

        cursor = self.get_cursor()
        cursor.execute(
            "DELETE FROM collection_tag WHERE collection_id=:collection_id",
            {"collection_id": collection_id},
        )

        cursor.execute(
            "DELETE FROM collection_author WHERE collection_id=:collection_id",
            {"collection_id": collection_id},
        )

        cursor.execute(
            "DELETE FROM collection_citation WHERE collection_id=:collection_id",
            {"collection_id": collection_id},
        )

        cursor.execute(
            "DELETE FROM collection_argument WHERE collection_id=:collection_id",
            {"collection_id": collection_id},
        )

        cursor.execute(
            "DELETE FROM collection_custom WHERE collection_id=:collection_id",
            {"collection_id": collection_id},
        )

        cursor.execute(
            "DELETE FROM collection_collection WHERE collection_id_child=:collection_id",
            {"collection_id": collection_id},
        )

        cursor.execute(
            "DELETE FROM cover WHERE collection_id=:collection_id",
            {"collection_id": collection_id},
        )

        cursor.execute(
            "DELETE FROM documentation WHERE collection_id=:collection_id",
            {"collection_id": collection_id},
        )

        cursor.execute(
            "DELETE FROM tag "
            "WHERE NOT EXISTS (SELECT st.tag_id FROM collection_tag st "
            "WHERE tag.tag_id = st.tag_id)"
        )

        cursor.execute(
            "DELETE FROM argument "
            "WHERE NOT EXISTS (SELECT sa.argument_id FROM collection_argument sa "
            "WHERE argument.argument_id = sa.argument_id)"
        )

        cursor.execute(
            "DELETE FROM citation "
            "WHERE NOT EXISTS (SELECT sc.collection_citation_id FROM collection_citation sc "
            "WHERE citation.citation_id = sc.citation_id)"
        )

        cursor.execute(
            "DELETE FROM author "
            "WHERE NOT EXISTS (SELECT sa.collection_author_id FROM collection_author sa "
            "WHERE author.author_id = sa.author_id)"
        )

        cursor.execute(
            "DELETE FROM custom "
            "WHERE NOT EXISTS (SELECT sa.custom_id FROM collection_custom sa "
            "WHERE custom.custom_id = sa.custom_id)"
        )

        # finally delete solution
        cursor.execute(
            "DELETE FROM collection "
            'WHERE catalog_id=:catalog_id AND "group"=:group AND name=:name AND version=:version',
            {
                "catalog_id": catalog_id,
                "group": coordinates.group(),
                "name": coordinates.name(),
                "version": coordinates.version(),
            },
        )

        if close:
            self.close_current_connection()

    def is_installed(self, catalog_id, coordinates: ICoordinates, close=True):
        r = self.get_solution_by_catalog_grp_name_version(
            catalog_id, coordinates, close=close
        )
        if not r:
            raise LookupError(f"Solution {catalog_id}:{coordinates} not found!")
        return True if r.internal()["installed"] else False

    def __len__(self, close=True):
        cursor = self.get_cursor()

        r = cursor.execute("SELECT COUNT(*) FROM collection").fetchone()
        r = r[0]

        if close:
            self.close_current_connection()

        return r

    @staticmethod
    def _as_db_col(key):
        if key == "group":
            return '"group"'
        return key

    @staticmethod
    def get_collection_column_keys():
        res = CatalogIndex.get_solution_column_keys()
        res.append("installed")
        res.append("installation_unfinished")
        res.append("last_execution")
        res.append("install_date")
        res.append("catalog_id")
        return res

import datetime
import sqlite3
import threading

from album.core.concept.singleton import Singleton
from album.core.model.configuration import Configuration
from album.core.model.default_values import DefaultValues


class SolutionsDb(metaclass=Singleton):
    # Singletons
    configuration = None

    connections = None
    cursors = None

    def __init__(self):
        self.configuration = Configuration()
        self.connections = {}
        self.cursors = {}

    def __del__(self):
        if self.connections:
            for thread_id in self.connections:
                self.connections[thread_id].close()

    def _get_connection(self):
        thread_id = threading.current_thread().ident
        if thread_id in self.connections:
            return self.connections[thread_id]
        con = self._create_connection()
        self.connections[thread_id] = con
        return con

    def get_cursor(self):
        thread_id = threading.current_thread().ident
        if thread_id in self.cursors:
            return self.cursors[thread_id]
        cursor = self._get_connection().cursor()
        self.cursors[thread_id] = cursor
        return cursor

    def _create_connection(self):
        con = sqlite3.connect(
            str(self.configuration.solutions_db_path.joinpath(DefaultValues.solutions_db_name.value))
        )
        con.row_factory = sqlite3.Row
        self.create(con)
        return con

    def is_empty(self):
        r = self.get_cursor().execute("SELECT * FROM installed_solutions").fetchone()
        return False if r else True

    @staticmethod
    def create(con):
        con.cursor().execute(
            "CREATE TABLE IF NOT EXISTS installed_solutions (solution_id INTEGER, catalog_id TEXT, grp TEXT, name TEXT, version TEXT, parent_id TEXT, install_date TEXT, last_execution TEXT)"
        )
        con.commit()

    def next_id(self):
        # note: always use subquery for count/max etc. operations as sqlite python API requires full rows back!
        if self.is_empty():
            return 1

        r = self.get_cursor().execute(
            "SELECT * FROM installed_solutions WHERE solution_id = (SELECT MAX(solution_id) FROM installed_solutions)"
        ).fetchone()
        return int(r["solution_id"]) + 1

    def add_solution(self, catalog_id, grp, name, version, parent_id):
        next_id = self.next_id()

        self.get_cursor().execute(
            "INSERT INTO installed_solutions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (next_id, catalog_id, grp, name, version, parent_id, datetime.datetime.now().isoformat(), None)
        )
        self._get_connection().commit()

    def get_all_solutions(self):
        installed_solutions_list = []
        cursor = self.get_cursor()
        for row in cursor.execute("SELECT * FROM installed_solutions"):
            installed_solutions_list.append(self._row_interpretation(row))

        return installed_solutions_list

    def get_solution_by_id(self, solution_id):
        r = self.get_cursor().execute(
            "SELECT * FROM installed_solutions WHERE solution_id=:solution_id",
            {
                "solution_id": solution_id,
            }).fetchall()

        if len(r) > 1:
            row = r[0]
            raise KeyError("Database error. Please remove solution %s:%s:%s from catalog %s !"
                           % (row["grp"], row["name"], row["version"], row["catalog_id"]))

        installed_solution = None
        for row in r:
            installed_solution = self._row_interpretation(row)

        return installed_solution

    def get_solution(self, catalog_id, grp, name, version):
        r = self.get_cursor().execute(
            "SELECT * FROM installed_solutions WHERE catalog_id=:catalog_id AND grp=:group AND name=:name AND version=:version",
            {
                "catalog_id": catalog_id,
                "group": grp,
                "name": name,
                "version": version,
            }
        ).fetchall()

        if len(r) > 1:
            raise KeyError("Database error. Please reinstall the solution %s:%s:%s from catalog %s !"
                           % (grp, name, version, catalog_id))

        installed_solution = None
        for row in r:
            installed_solution = self._row_interpretation(row)

        return installed_solution

    def get_solutions_by_grp_name_version(self, grp, name, version):
        installed_solutions_list = []
        cursor = self.get_cursor()
        for row in cursor.execute(
                "SELECT * FROM installed_solutions WHERE grp=:group AND name=:name AND version=:version",
                {
                    "group": grp,
                    "name": name,
                    "version": version,
                }
        ):
            installed_solutions_list.append(self._row_interpretation(row))

        return installed_solutions_list

    def is_installed(self, catalog_id, grp, name, version):
        r = self.get_cursor().execute(
            "SELECT * FROM installed_solutions WHERE catalog_id=:catalog_id AND grp=:group AND name=:name AND version=:version",
            {
                "catalog_id": catalog_id,
                "group": grp,
                "name": name,
                "version": version,
            }
        ).fetchone()

        return True if r else False

    def update_solution(self, catalog_id, grp, name, version):
        self.get_cursor().execute(
            "UPDATE installed_solutions SET last_execution=:cur_date WHERE catalog_id=:catalog_id AND grp=:group AND name=:name AND version=:version",
            {
                "catalog_id": catalog_id,
                "group": grp,
                "name": name,
                "version": version,
                "cur_date": datetime.datetime.now().isoformat()
            }
        )
        self._get_connection().commit()

    def remove_solution(self, catalog_id, grp, name, version):
        self.get_cursor().execute(
            "DELETE FROM installed_solutions WHERE catalog_id=:catalog_id AND grp=:group AND name=:name AND version=:version",
            {
                "catalog_id": catalog_id,
                "group": grp,
                "name": name,
                "version": version,
            }
        )
        self._get_connection().commit()

    @staticmethod
    def _row_interpretation(row):
        p_id = int(row["parent_id"]) if row["parent_id"] else None
        return {
            "solution_id": int(row["solution_id"]),
            "catalog_id": row["catalog_id"],
            "group": row["grp"],
            "name": row["name"],
            "version": row["version"],
            "parent_id": p_id,
            "installation_date": row["install_date"],
            "last_execution_date": row["last_execution"]
        }

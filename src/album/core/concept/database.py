import abc
import sqlite3
import threading
from pathlib import Path


class Database(abc.ABC):
    """Abstract class for all album sqlite databases"""
    # attributes
    connections = None
    cursors = None

    def __init__(self, path):
        self.connections = {}
        self.cursors = {}

        self.path = Path(path)

        if not self.is_created():
            self.create()

    def __del__(self):
        if self.connections:
            for thread_id in self.connections:
                self.connections[thread_id].close()
        self.cursors = {}
        self.connections = {}

    def get_connection(self):
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
        cursor = self.get_connection().cursor()
        self.cursors[thread_id] = cursor
        return cursor

    def _create_connection(self):
        con = sqlite3.connect(
            str(self.path)
        )
        con.row_factory = sqlite3.Row
        return con

    def next_id(self, table_name):
        table_name_id = table_name + "_id"
        is_empty = False if self.get_cursor().execute("SELECT * FROM %s" % table_name).fetchone() else True
        if is_empty:
            return 1

        # note: always use subquery for count/max etc. operations as sqlite python API requires full rows back!
        r = self.get_cursor().execute(
            "SELECT * FROM %s WHERE %s = (SELECT MAX(%s) FROM %s)" %
            (table_name, table_name_id, table_name_id, table_name)
        ).fetchone()
        return int(r[table_name_id]) + 1

    def is_created(self):
        r = self.get_cursor().execute("SELECT * FROM sqlite_master").fetchall()
        created = False

        for row in r:
            if row["name"] != "sqlite_sequence":
                created = True
                break

        return created

    @abc.abstractmethod
    def __len__(self):
        pass

    @abc.abstractmethod
    def create(self):
        pass

    @abc.abstractmethod
    def is_empty(self):
        pass



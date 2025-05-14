"""Implements the Database class which is a wrapper around the sqlite3 python module."""
import gc
import sqlite3
import threading
from abc import ABC
from pathlib import Path

from album.core.api.model.database import IDatabase


class Database(IDatabase, ABC):
    def __init__(self, path):
        self.connections = {}
        self.cursors = {}

        self.path = Path(path)

        if not self.is_created(close=False):
            self.create()

    def __del__(self):
        self.close()

    def close_current_connection(self, commit: bool = True) -> None:
        current_thread_id = threading.current_thread().ident
        if current_thread_id in self.cursors:
            cursor = self.cursors.pop(current_thread_id)
            cursor.close()

        if current_thread_id in self.connections:
            conn = self.connections.pop(current_thread_id)

            if commit:
                conn.commit()

            # finally close
            conn.close()

    def close(self) -> None:
        for cursor_id in self.cursors:
            cursor = self.cursors[cursor_id]
            try:
                cursor.close()
            except sqlite3.ProgrammingError:
                pass
            del cursor

        for thread_id in self.connections:
            connection = self.connections[thread_id]
            try:
                connection.close()
            except sqlite3.ProgrammingError:
                pass
            del connection

        gc.collect(2)
        self.cursors = {}
        self.connections = {}

    def get_connection(self) -> sqlite3.Connection:
        thread_id = threading.current_thread().ident
        if thread_id in self.connections:
            return self.connections[thread_id]
        con = self._create_connection()
        self.connections[thread_id] = con
        return con

    def get_cursor(self) -> sqlite3.Cursor:
        thread_id = threading.current_thread().ident
        if thread_id in self.cursors:
            return self.cursors[thread_id]
        cursor = self.get_connection().cursor()
        self.cursors[thread_id] = cursor
        return cursor

    def _create_connection(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.path))
        con.row_factory = sqlite3.Row
        return con

    def next_id(self, table_name: str, close=False) -> int:
        cursor = self.get_cursor()

        table_name_id = table_name + "_id"
        is_empty = (
            False
            if cursor.execute("SELECT * FROM %s" % table_name).fetchone()
            else True
        )
        if is_empty:
            return 1

        # note: always use subquery for count/max etc. operations as sqlite python API requires full rows back!
        r = cursor.execute(
            "SELECT * FROM %s WHERE %s = (SELECT MAX(%s) FROM %s)"
            % (table_name, table_name_id, table_name_id, table_name)
        ).fetchone()

        if close:
            cursor.connection.close()

        return int(r[table_name_id]) + 1

    def is_created(self, close: bool = True) -> bool:
        cursor = self.get_cursor()
        r = cursor.execute("SELECT * FROM sqlite_master").fetchall()
        created = False

        for row in r:
            if row["name"] != "sqlite_sequence":
                created = True
                break

        if close:
            cursor.connection.close()

        return created

    def is_table_empty(self, table: str, close: bool = True) -> bool:
        cursor = self.get_cursor()

        r = cursor.execute("SELECT * FROM %s" % table).fetchone()

        if close:
            self.close_current_connection()

        return False if r else True

    def get_path(self) -> Path:
        return self.path

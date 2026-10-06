import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from album.core.model.database import Database


class _TestDatabase(Database):
    """Minimal concrete database with a single table to test the base class."""

    def create(self) -> None:
        cursor = self.get_cursor()
        cursor.execute(
            "CREATE TABLE test_table (test_table_id INTEGER PRIMARY KEY, name TEXT)"
        )
        self.close_current_connection(commit=True)


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.database = _TestDatabase(Path(self.tmp_dir.name).joinpath("test_db.db"))

    def tearDown(self):
        self.database.close()
        self.database = None
        self.tmp_dir.cleanup()

    def insert_row(self, name: str) -> None:
        cursor = self.database.get_cursor()
        cursor.execute("INSERT INTO test_table (name) VALUES (?)", (name,))
        self.database.close_current_connection(commit=True)

    def select_all(self) -> list:
        return self.database.get_cursor().execute("SELECT * FROM test_table").fetchall()

    @unittest.skip("Needs to be implemented!")
    def test__init__(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test__del__(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_cursor(self):
        pass

    def test_next_id(self):
        self.assertEqual(1, self.database.next_id("test_table"))

        self.insert_row("a")
        self.insert_row("b")

        self.assertEqual(3, self.database.next_id("test_table"))

    def test_next_id_close(self):
        self.insert_row("a")
        thread_id = threading.current_thread().ident

        self.assertEqual(2, self.database.next_id("test_table", close=True))

        # the closed connection and its cursor must not stay cached
        self.assertNotIn(thread_id, self.database.connections)
        self.assertNotIn(thread_id, self.database.cursors)

        # a following query on the same database must work
        self.assertEqual(1, len(self.select_all()))

    def test_is_created(self):
        self.assertTrue(self.database.is_created(close=False))

        with patch.object(_TestDatabase, "create"):
            database = _TestDatabase(Path(self.tmp_dir.name).joinpath("empty_db.db"))
        self.assertFalse(database.is_created(close=False))
        database.close()

    def test_is_created_close(self):
        thread_id = threading.current_thread().ident

        self.assertTrue(self.database.is_created())

        # the closed connection and its cursor must not stay cached
        self.assertNotIn(thread_id, self.database.connections)
        self.assertNotIn(thread_id, self.database.cursors)

        # a following query on the same database must work
        self.assertEqual([], self.select_all())

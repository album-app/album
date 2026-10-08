import sqlite3
import tempfile
import threading
import time
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

    def assert_write_lock_free(self) -> None:
        # a connection that does not wait fails at once if anyone holds the write lock
        connection = sqlite3.connect(str(self.database.get_path()), timeout=0)
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.rollback()
        finally:
            connection.close()

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

    def test_next_id_close_empty_table(self):
        thread_id = threading.current_thread().ident

        self.assertEqual(1, self.database.next_id("test_table", close=True))

        # the connection is closed even for an empty table and holds no lock
        self.assertNotIn(thread_id, self.database.connections)
        self.assertNotIn(thread_id, self.database.cursors)
        self.assert_write_lock_free()

    def test_next_id_holds_write_lock_until_commit(self):
        next_id = self.database.next_id("test_table")

        # the id is reserved: nobody else can write before it is used and committed
        with self.assertRaises(sqlite3.OperationalError):
            self.assert_write_lock_free()

        self.database.get_cursor().execute(
            "INSERT INTO test_table VALUES (?, ?)", (next_id, "a")
        )
        self.database.close_current_connection()
        self.assert_write_lock_free()

    def test_next_id_concurrent_writers_get_distinct_ids(self):
        # a second database object on the same file stands in for another album process
        other = _TestDatabase(self.database.get_path())
        # only the writer thread below uses it, close what the constructor opened here
        other.close_current_connection()
        other_ids = []
        errors = []

        def other_writer():
            try:
                other_id = other.next_id("test_table")
                other.get_cursor().execute(
                    "INSERT INTO test_table VALUES (?, ?)", (other_id, "b")
                )
                other.close_current_connection()
                other_ids.append(other_id)
            except sqlite3.Error as e:
                errors.append(e)
            finally:
                other.close_current_connection(commit=False)

        first_id = self.database.next_id("test_table")
        thread = threading.Thread(target=other_writer)
        thread.start()

        # the other writer has to wait instead of reading the same MAX(id)
        thread.join(0.5)
        self.assertTrue(thread.is_alive())

        self.database.get_cursor().execute(
            "INSERT INTO test_table VALUES (?, ?)", (first_id, "a")
        )
        self.database.close_current_connection()
        thread.join(10)

        self.assertFalse(thread.is_alive())
        self.assertEqual([], errors)
        self.assertEqual([1, 2], [first_id] + other_ids)
        self.assertEqual(2, len(self.select_all()))

    def test_next_id_waits_for_the_lock_with_a_pending_read(self):
        self.insert_row("a")
        self.insert_row("b")
        # a read on the cached cursor that was not fetched to the end
        self.database.get_cursor().execute("SELECT * FROM test_table").fetchone()

        # another album process holds the write lock for a moment
        locked = threading.Event()
        errors = []

        def other_writer():
            connection = sqlite3.connect(str(self.database.get_path()), timeout=10)
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("INSERT INTO test_table VALUES (3, 'c')")
                locked.set()
                time.sleep(1)
                connection.commit()
            except sqlite3.Error as e:
                errors.append(e)
                locked.set()
            finally:
                connection.close()

        thread = threading.Thread(target=other_writer)
        thread.start()
        try:
            self.assertTrue(locked.wait(10))

            # waits for the lock (busy timeout) instead of failing at once
            next_id = self.database.next_id("test_table")
        finally:
            self.database.close_current_connection(commit=False)
            thread.join(15)

        self.assertFalse(thread.is_alive())
        self.assertEqual([], errors)
        self.assertEqual(4, next_id)

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

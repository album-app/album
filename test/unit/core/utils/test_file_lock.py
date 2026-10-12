import errno
import os
import stat
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from test.unit.test_unit_core_common import TestUnitCoreCommon
from unittest.mock import patch

from album.core.utils.file_lock import FileLock

# holds the lock given as first argument until a line is read from stdin
LOCK_HOLDER = """
import sys
from album.core.utils.file_lock import FileLock

with FileLock(sys.argv[1], timeout=10, description="testing"):
    print("locked", flush=True)
    sys.stdin.readline()
"""


class TestFileLock(TestUnitCoreCommon):
    def setUp(self):
        super().setUp()
        self.lock_path = Path(self.tmp_dir.name).joinpath("install.lock")

    def tearDown(self) -> None:
        super().tearDown()

    def _lock(self, timeout: float = 0.2) -> FileLock:
        return FileLock(
            self.lock_path, timeout=timeout, description="testing", poll_interval=0.01
        )

    def _start_lock_holder(self) -> subprocess.Popen:
        holder = subprocess.Popen(
            [sys.executable, "-c", LOCK_HOLDER, str(self.lock_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(holder.wait, 10)
        self.addCleanup(holder.kill)
        self.assertEqual("locked", holder.stdout.readline().strip())
        return holder

    def test_acquire_release(self):
        lock = self._lock()

        lock.acquire()
        self.assertTrue(self.lock_path.is_file())
        lock.release()

        # another lock on the same file is free again, the lock file stays
        with self._lock():
            pass
        self.assertTrue(self.lock_path.is_file())

    def test_acquire_creates_parent_folder(self):
        self.lock_path = Path(self.tmp_dir.name).joinpath("not", "there", "a.lock")

        with self._lock():
            self.assertTrue(self.lock_path.is_file())

    def test_held_lock_times_out(self):
        waiting = self._lock(timeout=0.2)
        with self._lock():
            start = time.monotonic()
            with self.assertRaises(TimeoutError) as context:
                waiting.acquire()

        self.assertGreaterEqual(time.monotonic() - start, 0.2)
        self.assertIn(str(self.lock_path), str(context.exception))
        self.assertIn(
            "Waiting for another album process or thread to finish testing",
            self.get_logs_as_string(),
        )

        # the lock that timed out can be acquired once it is free
        with waiting:
            pass

    def test_reentrant(self):
        lock = self._lock()

        with lock:
            with lock:
                pass
            # the inner release keeps the lock
            with self.assertRaises(TimeoutError):
                self._lock(timeout=0).acquire()

        with self._lock(timeout=0):
            pass

    def test_acquire_not_blocking(self):
        lock = self._lock(timeout=5)

        # free, and re-entered by the holding thread
        self.assertTrue(lock.acquire(blocking=False))
        self.assertTrue(lock.acquire(blocking=False))
        lock.release()
        lock.release()

        holding = threading.Event()
        done = threading.Event()

        def hold():
            with lock:
                holding.set()
                done.wait(5)

        thread = threading.Thread(target=hold)
        thread.start()
        holding.wait(5)
        try:
            start = time.monotonic()
            # held by another thread
            self.assertFalse(lock.acquire(blocking=False))
            # held through the lock file, as seen by another lock on it
            self.assertFalse(self._lock(timeout=5).acquire(blocking=False))
            # returned right away, without waiting
            self.assertLess(time.monotonic() - start, 1)
        finally:
            done.set()
            thread.join()

        self.assertNotIn("Waiting", self.get_logs_as_string())
        # nothing is kept from the failed attempts
        with self._lock(timeout=0):
            pass
        self.assertTrue(lock.acquire(blocking=False))
        lock.release()

    def test_acquire_not_blocking_other_process(self):
        holder = self._start_lock_holder()
        lock = self._lock(timeout=5)

        start = time.monotonic()
        self.assertFalse(lock.acquire(blocking=False))
        self.assertLess(time.monotonic() - start, 1)
        self.assertNotIn("Waiting", self.get_logs_as_string())

        # the lock is acquired once the other process released it
        holder.stdin.write("\n")
        holder.stdin.flush()
        holder.wait(10)
        self.assertTrue(lock.acquire(blocking=False))
        lock.release()

    def test_is_held_by_current_thread(self):
        lock = self._lock()
        held_in_other_thread = []

        self.assertFalse(lock.is_held_by_current_thread())
        with lock:
            self.assertTrue(lock.is_held_by_current_thread())
            thread = threading.Thread(
                target=lambda: held_in_other_thread.append(
                    lock.is_held_by_current_thread()
                )
            )
            thread.start()
            thread.join()

        self.assertEqual([False], held_in_other_thread)
        self.assertFalse(lock.is_held_by_current_thread())

    def test_release_not_held(self):
        lock = self._lock()

        with self.assertRaises(RuntimeError):
            lock.release()

        # releasing from another thread than the holding one
        errors = []

        def release():
            try:
                lock.release()
            except RuntimeError as e:
                errors.append(e)

        with lock:
            thread = threading.Thread(target=release)
            thread.start()
            thread.join()
        self.assertEqual(1, len(errors))

    def test_threads_wait_for_each_other(self):
        lock = self._lock(timeout=5)
        events = []
        holding = threading.Event()

        def hold():
            with lock:
                events.append("first acquired")
                holding.set()
                time.sleep(0.2)
                events.append("first released")

        def wait():
            holding.wait(5)
            with lock:
                events.append("second acquired")

        threads = [threading.Thread(target=hold), threading.Thread(target=wait)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(
            ["first acquired", "first released", "second acquired"], events
        )

    def test_thread_times_out(self):
        lock = self._lock(timeout=5)
        holding = threading.Event()
        done = threading.Event()

        def hold():
            with lock:
                holding.set()
                done.wait(5)

        thread = threading.Thread(target=hold)
        thread.start()
        holding.wait(5)
        try:
            lock._timeout = 0.1
            with self.assertRaises(TimeoutError):
                lock.acquire()
        finally:
            done.set()
            thread.join()

    def test_other_process_holds_lock(self):
        holder = self._start_lock_holder()
        lock = self._lock(timeout=0.2)

        with self.assertRaises(TimeoutError):
            lock.acquire()

        # the lock is free once the other process released it
        holder.stdin.write("\n")
        holder.stdin.flush()
        holder.wait(10)
        with lock:
            pass

    def test_process_ended_without_releasing(self):
        holder = self._start_lock_holder()

        holder.kill()
        holder.wait(10)

        # the operating system released the lock, no stale lock is left behind
        with self._lock(timeout=5):
            pass

    def test_read_only_lock_file(self):
        # e.g. created by another user in a shared base path
        self.lock_path.touch()
        os.chmod(self.lock_path, stat.S_IREAD)
        try:
            holder = self._start_lock_holder()

            # the lock file is locked although it cannot be written
            with self.assertRaises(TimeoutError):
                self._lock(timeout=0.2).acquire()

            holder.stdin.write("\n")
            holder.stdin.flush()
            holder.wait(10)
            lock = self._lock(timeout=5)
            with lock:
                self.assertIsNotNone(lock._fd)
        finally:
            os.chmod(self.lock_path, stat.S_IREAD | stat.S_IWRITE)

        self.assertNotIn("Cannot lock", self.get_logs_as_string())

    @patch("album.core.utils.file_lock._lock_fd")
    def test_locking_not_supported(self, lock_fd):
        lock_fd.side_effect = OSError(errno.ENOSYS, "Function not implemented")
        lock = self._lock()

        # proceed without the lock, as before the lock existed
        with lock:
            self.assertIsNone(lock._fd)

        self.assertIn("Cannot lock", self.get_logs_as_string())

    def test_lock_file_cannot_be_created(self):
        # the parent "folder" of the lock file is a file
        self.lock_path = Path(self.closed_tmp_file.name).joinpath("install.lock")
        lock = self._lock()

        with lock:
            self.assertIsNone(lock._fd)

        self.assertIn("Cannot lock", self.get_logs_as_string())


if __name__ == "__main__":
    unittest.main()

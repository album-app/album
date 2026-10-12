"""A lock shared by all threads and processes using the same lock file."""

import errno
import os
import sys
import threading
import time
from pathlib import Path
from types import TracebackType
from typing import Optional, Type, Union

from album.runner import album_logging

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

module_logger = album_logging.get_active_logger

# errors of a non-blocking lock attempt meaning that someone else holds the lock.
# Every other error means the file system does not support locking.
_LOCK_HELD_ERRNOS = {errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK, errno.EDEADLK}


def _lock_fd(fd: int) -> None:
    """Lock the first byte of the open file without blocking, raise OSError if held."""
    if sys.platform == "win32":
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_fd(fd: int) -> None:
    if sys.platform == "win32":
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(fd, fcntl.LOCK_UN)


class FileLock:
    """Re-entrant lock held by at most one thread of one process at a time.

    Processes coordinate through an operating system lock on the lock file
    (msvcrt.locking on Windows, fcntl.flock elsewhere), threads of the same process
    through a threading lock. The thread holding the lock can acquire it again.

    The operating system releases the lock when the holding process ends, so a
    crashed process never leaves a stale lock behind. The lock file is therefore
    never removed: removing it while it is held would let another process lock a
    new file of the same name.

    When the file system does not support locking, a warning is logged and the
    lock only coordinates the threads of this process.
    """

    def __init__(
        self,
        path: Union[str, Path],
        timeout: float,
        description: str,
        poll_interval: float = 0.5,
    ):
        """Create the lock, the lock file is only created when the lock is acquired.

        Args:
            path:
                The lock file.
            timeout:
                Seconds to wait for the lock before raising a TimeoutError.
            description:
                What the lock protects, used in log messages, e.g. 'installing "a:b:c"'.
            poll_interval:
                Seconds to wait between two attempts to lock the lock file.
        """
        self._path = Path(path)
        self._timeout = timeout
        self._description = description
        self._poll_interval = poll_interval
        self._thread_lock = threading.Lock()
        self._owner: Optional[int] = None  # ident of the thread holding the lock
        self._count = 0  # how often the owner acquired the lock
        self._fd: Optional[int] = None  # the locked lock file

    def acquire(self, blocking: bool = True) -> bool:
        """Acquire the lock, waiting for other threads and processes holding it.

        Args:
            blocking:
                When False, do not wait: return False right away when another thread
                or process holds the lock.

        Returns:
            True when the lock was acquired, False only when not blocking.

        Raises:
            TimeoutError: when the lock could not be acquired within the timeout.
        """
        if self._owner == threading.get_ident():
            self._count += 1
            return True
        deadline = time.monotonic() + (self._timeout if blocking else 0)
        waiting = False
        if not self._thread_lock.acquire(blocking=False):
            if not blocking:
                return False
            self._log_waiting()
            waiting = True
            if not self._thread_lock.acquire(
                timeout=max(0.0, deadline - time.monotonic())
            ):
                raise self._timeout_error()
        try:
            self._fd = self._lock_file(deadline, waiting)
        except BaseException as e:
            self._thread_lock.release()
            if not blocking and isinstance(e, TimeoutError):
                return False  # another process holds the lock file
            raise
        self._owner = threading.get_ident()
        self._count = 1
        return True

    def is_held_by_current_thread(self) -> bool:
        """Return whether the calling thread holds the lock."""
        return self._owner == threading.get_ident()

    def release(self) -> None:
        """Release the lock, it is unlocked when the outermost acquire is released.

        Raises:
            RuntimeError: when the calling thread does not hold the lock.
        """
        if self._owner != threading.get_ident():
            raise RuntimeError("Cannot release a lock that is not held.")
        self._count -= 1
        if self._count > 0:
            return
        self._owner = None
        try:
            if self._fd is not None:
                try:
                    _unlock_fd(self._fd)
                finally:
                    os.close(self._fd)
        finally:
            self._fd = None
            self._thread_lock.release()

    def __enter__(self) -> "FileLock":
        """Acquire the lock, see acquire()."""
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Release the lock, see release()."""
        self.release()

    def _open_lock_file(self) -> int:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            return os.open(self._path, os.O_RDWR | os.O_CREAT, 0o666)
        except PermissionError:
            # e.g. a lock file another user created in a shared base path. Both
            # msvcrt.locking and flock also lock a file opened read-only.
            return os.open(self._path, os.O_RDONLY)

    def _lock_file(self, deadline: float, waiting: bool) -> Optional[int]:
        try:
            fd = self._open_lock_file()
        except OSError as e:
            self._log_unsupported(e)
            return None
        try:
            while True:
                try:
                    _lock_fd(fd)
                    return fd
                except OSError as e:
                    if e.errno not in _LOCK_HELD_ERRNOS:
                        self._log_unsupported(e)
                        os.close(fd)
                        return None
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise self._timeout_error()
                if not waiting:
                    self._log_waiting()
                    waiting = True
                time.sleep(min(self._poll_interval, remaining))
        except BaseException:
            os.close(fd)
            raise

    def _log_waiting(self) -> None:
        module_logger().info(
            "Waiting for another album process or thread to finish %s "
            '(lock file "%s")...' % (self._description, str(self._path))
        )

    def _log_unsupported(self, error: OSError) -> None:
        module_logger().warning(
            'Cannot lock "%s" (%s). Album processes %s at the same time '
            "might interfere with each other."
            % (str(self._path), error, self._description)
        )

    def _timeout_error(self) -> TimeoutError:
        return TimeoutError(
            'Gave up waiting for the lock file "%s" after %s seconds: another album '
            "process or thread is still %s. Try again once it has finished."
            % (str(self._path), self._timeout, self._description)
        )

"""Interface for a task that can be executed by the task manager."""
from abc import ABCMeta, abstractmethod
from enum import IntEnum, unique
from logging import Handler, LogRecord
from typing import Callable, List, Optional


class ILogHandler(Handler):
    """Interface for a log handler that can be used to store log records."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def emit(self, record: LogRecord) -> None:
        """Emit a log record to the log handler."""
        raise NotImplementedError

    @abstractmethod
    def records(self):
        """Get the stored log records."""
        raise NotImplementedError


class ITask:
    """Interface for a task that can be executed by the task manager."""

    __metaclass__ = ABCMeta

    @unique
    class Status(IntEnum):
        """Enum for the status of a task."""

        WAITING = 0
        RUNNING = 1
        FINISHED = 2
        FAILED = 3
        UNDEFINED = 4

    @abstractmethod
    def id(self) -> str:
        """Get the ID of the task."""
        raise NotImplementedError

    @abstractmethod
    def method(self) -> Callable:
        """Get the method that should be executed by the task manager."""
        raise NotImplementedError

    @abstractmethod
    def args(self) -> List[str]:
        """Get the arguments that should be passed to the method."""
        raise NotImplementedError

    @abstractmethod
    def log_handler(self) -> Optional[ILogHandler]:
        """Get the log handler that should be used to store log records."""
        raise NotImplementedError

    @abstractmethod
    def status(self) -> Status:
        """Get the status of the task."""
        raise NotImplementedError

    @abstractmethod
    def set_status(self, status) -> None:
        """Set the status of the task."""
        raise NotImplementedError

    @abstractmethod
    def set_log_handler(self, handler) -> None:
        """Set the log handler that should be used to store log records."""
        raise NotImplementedError

    @abstractmethod
    def set_id(self, task_id: str) -> None:
        """Set the ID of the task."""
        raise NotImplementedError

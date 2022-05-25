from abc import ABCMeta, abstractmethod
from enum import unique, IntEnum
from logging import Handler, LogRecord


class ILogHandler(Handler):
    __metaclass__ = ABCMeta

    @abstractmethod
    def emit(self, record: LogRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def records(self):
        raise NotImplementedError


class ITask:
    __metaclass__ = ABCMeta

    @unique
    class Status(IntEnum):
        WAITING = 0
        RUNNING = 1
        FINISHED = 2
        FAILED = 3

    @abstractmethod
    def id(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def method(self):
        raise NotImplementedError

    @abstractmethod
    def args(self):
        raise NotImplementedError

    @abstractmethod
    def log_handler(self):
        raise NotImplementedError

    @abstractmethod
    def status(self) -> Status:
        raise NotImplementedError

    @abstractmethod
    def set_status(self, status):
        raise NotImplementedError

    @abstractmethod
    def set_log_handler(self, handler):
        raise NotImplementedError

    @abstractmethod
    def set_id(self, task_id: str):
        raise NotImplementedError

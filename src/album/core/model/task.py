"""Implements the ITask interface."""
from logging import LogRecord
from typing import Callable, List, Optional

from album.core.api.model.task import ILogHandler, ITask


class LogHandler(ILogHandler):
    def __init__(self):
        super().__init__()
        self._records = []

    def emit(self, record: LogRecord) -> None:
        self._records.append(record)

    def records(self):
        return self._records


class Task(ITask):
    _id: Optional[str] = None
    _method: Optional[Callable] = None
    _args: Optional[List[str]] = None
    _log_handler: Optional[ILogHandler] = None
    _status: ITask.Status = ITask.Status.UNDEFINED

    def __init__(
        self,
        method: Callable,
        args: Optional[List[str]] = None,
    ):
        self._method = method
        if args:
            self._args = args

    def id(self) -> str:
        if self._id is None:
            raise NotImplementedError("ID not set!")
        return self._id

    def method(self) -> Callable:
        if self._method is None:
            raise NotImplementedError("Method not set!")
        return self._method

    def args(self) -> List[str]:
        args = self._args
        if args is None:
            args = []
        return args

    def log_handler(self) -> Optional[ILogHandler]:
        return self._log_handler

    def status(self) -> ITask.Status:
        return self._status

    def set_status(self, status: ITask.Status) -> None:
        self._status = status

    def set_log_handler(self, handler: ILogHandler) -> None:
        self._log_handler = handler

    def set_id(self, new_id: str) -> None:
        self._id = new_id

from logging import LogRecord

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
    _id = None
    _method = None
    _args = tuple()
    _log_handler: LogHandler = None
    _status: ITask.Status = None

    def __init__(self, method=None, args=None):
        self._method = method
        if args:
            self._args = args

    def id(self):
        return self._id

    def method(self):
        return self._method

    def args(self):
        return self._args

    def log_handler(self):
        return self._log_handler

    def status(self) -> ITask.Status:
        return self._status

    def set_status(self, status):
        self._status = status

    def set_log_handler(self, handler):
        self._log_handler = handler

    def set_id(self, new_id):
        self._id = new_id

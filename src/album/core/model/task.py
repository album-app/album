from enum import unique, IntEnum
from logging import Handler, LogRecord


class LogHandler(Handler):
    records = []

    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record: LogRecord) -> None:
        self.records.append(record)


class Task:
    @unique
    class Status(IntEnum):
        WAITING = 0
        RUNNING = 1
        FINISHED = 2
        FAILED = 3

    id = None
    method = None
    args = tuple()
    log_handler: LogHandler = None
    status: Status = None

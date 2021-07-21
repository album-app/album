from enum import unique, IntEnum

from album.core.model.log_handler import LogHandler


class Task:
    @unique
    class Status(IntEnum):
        WAITING = 0
        RUNNING = 1
        FINISHED = 2

    id = None
    method = None
    solution_path = None
    sysarg = []
    log_handler: LogHandler = None
    status: Status = None


from logging import Handler, LogRecord


class LogHandler(Handler):
    records = []

    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record: LogRecord) -> None:
        self.records.append(record)

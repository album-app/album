"""Core logging utilities for Album."""

import logging
import re
import shutil
import sys
import time
from typing import Optional

from album.core.utils.operations.view_operations import (
    get_logger_name_minimizer_filter,
    get_logging_formatter,
    get_message_filter,
)
from album.runner.album_logging import (
    LogLevel,
    debug_settings,
    push_active_logger,
    set_loglevel,
)

# Progress updates are lines a solution redraws, like the progress bars of tqdm.
# album-environments gives their log records the attribute album_progress. Where the
# output is no terminal (a log file, CI), one per PROGRESS_LOG_INTERVAL seconds is written.
PROGRESS_LOG_INTERVAL = 30

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


class ProgressLineHandler(logging.StreamHandler):
    """Stream handler for a terminal: a progress update replaces the one before."""

    progress_rows = 0  # rows of the progress update on screen

    def emit(self, record: logging.LogRecord) -> None:
        """Write the record, a progress update without a line break."""
        try:
            if self.progress_rows:  # erase the progress update, the record replaces it
                # back to the first row of the update ("\x1b[<n>A": n rows up), then
                # erase to the end of the screen ("\x1b[J")
                up = self.progress_rows - 1
                self.stream.write("\r" + ("\x1b[%dA" % up if up else "") + "\x1b[J")
                self.progress_rows = 0
            if not getattr(record, "album_progress", False):
                super().emit(record)
                return
            # an update wider than the terminal wraps, it is written whole
            line = _ANSI_ESCAPE.sub("", self.format(record))
            columns = max(shutil.get_terminal_size().columns, 1)
            if len(line) % columns == 0:
                line += " "  # so the cursor ends in the last row on every terminal
            self.stream.write(line)
            self.flush()
            self.progress_rows = len(line) // columns + 1
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)


class ProgressIntervalFilter(logging.Filter):
    """Let a progress update pass at most once per interval, other records always."""

    def __init__(self, interval: float):
        """Initialize the filter with the interval in seconds."""
        super().__init__()
        self.interval = interval
        self.last_progress = float("-inf")

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        """Return whether the record is written."""
        if not getattr(record, "album_progress", False):
            return True
        now = time.monotonic()
        if now - self.last_progress < self.interval:
            return False
        self.last_progress = now
        return True


def configure_root_logger(
    log_format: Optional[str] = None,
    log_format_time: Optional[str] = None,
    log_level: Optional[LogLevel] = None,
):
    """Configure the root logger."""
    if not log_level:
        log_level = LogLevel(debug_settings())
    logger = logging.getLogger("album")
    logger.setLevel(log_level.name)
    # create console handler and set level to debug
    # ToDo: different handlers necessary? e.g. logging additional into a file?
    ch: logging.StreamHandler
    if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
        ch = ProgressLineHandler(stream=sys.stdout)
    else:
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.addFilter(ProgressIntervalFilter(PROGRESS_LOG_INTERVAL))
    ch.setLevel(log_level.name)

    # add formatter to ch
    ch.setFormatter(get_logging_formatter(fmt=log_format, time=log_format_time))
    ch.addFilter(get_logger_name_minimizer_filter())
    ch.addFilter(get_message_filter())

    # add ch to logger
    logger.addHandler(ch)
    set_loglevel(log_level)
    push_active_logger(logger)


def add_logging_level(levelName, levelNum, methodName=None):
    """Add a new logging level to the `logging` module and the currently configured logging class.

    Copied from https://stackoverflow.com/a/35804945

    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    `levelName` becomes an attribute of the `logging` module with the value
    `levelNum`. `methodName` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `methodName` is not specified, `levelName.lower()` is
    used.

    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present

    Example
    -------
    >>> add_logging_level('TRACE', logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace('that worked')
    >>> logging.trace('so did this')
    >>> logging.TRACE
    5

    """
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
        raise AttributeError(f"{levelName} already defined in logging module")
    if hasattr(logging, methodName):
        raise AttributeError(f"{methodName} already defined in logging module")
    if hasattr(logging.getLoggerClass(), methodName):
        raise AttributeError(f"{methodName} already defined in logger class")

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)

    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)

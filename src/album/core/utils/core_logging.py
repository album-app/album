import logging
import sys

from album.core.utils.operations.view_operations import (
    get_logger_name_minimizer_filter,
    get_logging_formatter,
    get_message_filter,
)
from album.runner.album_logging import (
    set_loglevel,
    debug_settings,
    LogLevel,
    push_active_logger,
)


def configure_root_logger(
    log_format: str = None, log_format_time: str = None, log_level: LogLevel = None
):
    if not log_level:
        log_level = LogLevel(debug_settings())
    logger = logging.getLogger("album")
    logger.setLevel(log_level.name)
    # create console handler and set level to debug
    # ToDo: different handlers necessary? e.g. logging additional into a file?
    ch = logging.StreamHandler(stream=sys.stdout)
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
    """
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
        raise AttributeError("{} already defined in logging module".format(levelName))
    if hasattr(logging, methodName):
        raise AttributeError("{} already defined in logging module".format(methodName))
    if hasattr(logging.getLoggerClass(), methodName):
        raise AttributeError("{} already defined in logger class".format(methodName))

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

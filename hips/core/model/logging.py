import io
import logging
import re
from enum import IntEnum, unique

"""
Global variable for tracking the currently active logger. Do not use this
directly instead use get_active_logger()
"""
global _active_logger
_active_logger = []

DEBUG = False


def push_active_logger(logger):
    """Insert a logger to the _active_logger stack."""
    global _active_logger
    _active_logger.insert(0, logger)


def get_active_logger():
    """Return the currently active logger, which is defined globally."""
    global _active_logger
    if len(_active_logger) > 0:
        return _active_logger[0]
    return logging.getLogger()  # root logger


def pop_active_logger():
    """Pop the currently active logger from the _active_hips stack."""
    global _active_logger

    if len(_active_logger) > 0:
        logger = _active_logger.pop(0)
        while logger.hasHandlers():
            logger.removeHandler(logger.handlers[0])
        return logger
    else:
        return logging.getLogger()  # root logger


@unique
class LogLevel(IntEnum):
    """LogLevel hips allows.

    Notes:
        Only add Names available in python standard logging module.

    """
    DEBUG = 1
    INFO = 0
    WARNING = 2


def to_loglevel(value):
    """Converts a string value to a @LogLevel.

    Args:
        value:
            The string value

    Returns:
        The LovLevel class enum

    Raises:
        KeyError when loglevel unknown.

    """
    try:
        return LogLevel[value]
    except KeyError as err:
        logger = get_active_logger()
        logger.error('Loglevel %s not allowed or unknown!' % value)
        raise err


def configure_logging(loglevel, name, stream_handler=None, formatter_string=None):
    """Configures a logger with a certain name and loglevel.

    Args:
        stream_handler:
            Optional. A stream handler to configure logging for
        formatter_string:
            A formatter string.
        loglevel:
            The Loglevel to use. Either DEBUG or INFO.
        name:
            The name of the logger.

    Returns:
        The logger object.

    """
    # create logger
    logger = logging.getLogger(name)

    if not logger.hasHandlers():
        logger.setLevel(loglevel.name)

        # create formatter
        if not formatter_string:
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        else:
            formatter = logging.Formatter(formatter_string)

        # create console handler and set level to debug
        # ToDo: different handlers necessary? e.g. logging additional into a file?
        if not stream_handler:
            ch = logging.StreamHandler()
        else:
            ch = logging.StreamHandler(stream_handler)

        ch.setLevel(loglevel.name)

        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch to logger
        logger.addHandler(ch)

        # push logger
        push_active_logger(logger)

    return logger


def get_loglevel_name():
    """Returns the Name of the loglevel of the current active logger."""
    logger = get_active_logger()
    return logging.getLevelName(logger.level)


def set_loglevel(loglevel):
    """ Sets logLevel for a logger with a certain name for ALL available handlers.

    Args:
        loglevel:
            The Loglevel to use. Either DEBUG or INFO.
        name:
            The name of the logger.

    """
    # logger loglevel
    active_logger = get_active_logger()
    active_logger.debug('Set loglevel to %s...' % loglevel.name)

    active_logger.setLevel(loglevel.name)

    # set handler loglevel
    for handler in active_logger.handlers:
        handler_name = handler.stream.name if hasattr(handler.stream, active_logger.name) else "default handler"

        active_logger.debug('Set loglevel for handler %s to %s...' % (handler_name, loglevel.name))
        handler.setLevel(loglevel.name)


class LogfileBuffer(io.StringIO):
    """Class for logging in a subprocess. Logs to the current active logger."""

    def __init__(self, message_formatter=None):
        super().__init__()
        self.module_logger = get_active_logger
        self.message_formatter = message_formatter

    def write(self, s: str) -> int:
        s = self.tabulate_multi_lines(s)

        r = re.search('^([^-]+) - ([^-]+) - ((?:.|\n)+)', s)
        if r:
            name = r.group(1)
            level = r.group(2)
            message = r.group(3)

            if self.message_formatter and callable(self.message_formatter):
                message = self.message_formatter(message)

            old_name = self.module_logger().name
            self.module_logger().name = name

            if LogLevel.INFO.name == level:
                self.module_logger().info(message)
            elif LogLevel.DEBUG.name == level:
                self.module_logger().debug(message)
            elif LogLevel.WARNING.name == level:
                self.module_logger().warning(message)

            self.module_logger().name = old_name

        else:  # unknown message not using print or logging.
            self.module_logger().info(s)

        return 1

    @staticmethod
    def tabulate_multi_lines(s: str, indent=2):
        split_s = s.strip().split("\n")
        r = split_s[0].strip()
        if len(split_s) > 1:
            r = r + "\n"
            for l in split_s[1:]:
                r = r + "".join(["\t"] * indent) + l.strip() + "\n"
        return r.strip()


def hips_debug():
    return DEBUG

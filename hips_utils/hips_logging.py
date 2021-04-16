import logging
from enum import IntEnum, unique


"""
Global variable for tracking the currently active logger. Do not use this
directly instead use get_active_logger()
"""
global _active_logger
_active_logger = []


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


def configure_logging(loglevel, name):
    """Configures a logger with a certain name and loglevel.

    Args:
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

        # create console handler and set level to debug
        # ToDo: different handlers necessary? e.g. logging additional into a file?
        ch = logging.StreamHandler()
        ch.setLevel(loglevel.name)

        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch to logger
        logger.addHandler(ch)

        # push logger
        push_active_logger(logger)

    return logger


def get_loglevel_name():
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

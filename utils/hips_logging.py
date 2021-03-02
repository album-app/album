import logging
from enum import IntEnum, unique


@unique
class LogLevel(IntEnum):
    """LogLevel hips allows.

    Notes:
        Only add Names available in python standard logging module.

    """
    DEBUG = 1
    INFO = 0


def to_loglevel(value, name):
    """Converts a string value to a @LogLevel.

    Args:
        value:
            The string value
        name:
            The name of the logger

    Returns:
        The LovLevel class enum

    Raises:
        KeyError when loglevel unknown.

    """
    try:
        return LogLevel[value]
    except KeyError as err:
        logger = logging.getLogger(name)
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

    return logger


def set_loglevel(loglevel, name):
    """ Sets logLevel for a logger with a certain name for ALL available handlers.

    Args:
        loglevel:
            The Loglevel to use. Either DEBUG or INFO.
        name:
            The name of the logger.

    """
    # logger loglevel
    logger = logging.getLogger(name)
    logger.debug('Set loglevel to %s...' % loglevel.name)

    logger.setLevel(loglevel.name)

    # set handler loglevel
    for handler in logger.handlers:
        handler_name = handler.stream.name if hasattr(handler.stream, name) else "default handler"

        logger.debug('Set loglevel for handler %s to %s...' % (handler_name, loglevel.name))
        handler.setLevel(loglevel.name)

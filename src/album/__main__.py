import logging

from album.argument_parsing import main
from album.runner.album_logging import debug_settings, get_active_logger, configure_root_logger, LogLevel

module_logger = get_active_logger


def startup():
    __retrieve_logger()
    main()


def __retrieve_logger():
    """Retrieves the default album logger."""
    configure_root_logger(LogLevel(debug_settings()))
    logging.getLogger().name = "album"


if __name__ == "__main__":
    startup()

import album
from album.argument_parsing import main
from album.runner import logging
from album.runner.logging import debug_settings

module_logger = logging.get_active_logger


def startup():
    __retrieve_logger()
    main()


def __retrieve_logger():
    """Retrieves the default album logger."""
    logging.configure_root_logger(logging.LogLevel(debug_settings()))


if __name__ == "__main__":
    startup()

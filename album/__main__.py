import album
from album.argument_parsing import main
from album_runner import logging
from album_runner.logging import debug_settings

module_logger = logging.get_active_logger


def startup():
    __retrieve_logger()
    module_logger().info(
        "Running album version %s \n \n %s - contact via %s " %
        (album.__version__, album.__author__, album.__email__))
    main()


def __retrieve_logger():
    """Retrieves the default album logger."""
    logging.configure_root_logger(logging.LogLevel(debug_settings()))


if __name__ == "__main__":
    startup()

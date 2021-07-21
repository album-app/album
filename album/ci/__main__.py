import album
from album.ci.argument_parsing import main
from album_runner import logging
from album_runner.logging import get_active_logger, debug_settings

module_logger = get_active_logger


def startup():
    __retrieve_logger()
    module_logger().info(
        "Running album-ci version %s \n \n %s - contact via %s " %
        (album.ci.__version__, album.ci.__author__, album.ci.__email__))
    main()


def __retrieve_logger():
    """Retrieves the default album ci logger."""
    logging.configure_logging(logging.LogLevel(debug_settings()), 'album_ci')


if __name__ == '__main__':
    startup()



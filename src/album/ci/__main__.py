import album
from album.ci.argument_parsing import main
from album.core.utils.core_logging import configure_root_logger
from album.runner import album_logging
from album.runner.album_logging import get_active_logger, debug_settings

module_logger = get_active_logger


def startup():
    __retrieve_logger()
    module_logger().info(
        "Running album-catalog-admin version %s \n \n %s - contact via %s "
        % (album.ci.__version__, album.ci.__author__, album.ci.__email__)
    )
    main()


def __retrieve_logger():
    """Retrieves the default album ci logger."""
    configure_root_logger(album_logging.LogLevel(debug_settings()))


if __name__ == "__main__":
    startup()

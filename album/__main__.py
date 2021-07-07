import album
from album.argument_parsing import main
from album.core.controller.catalog_manager import CatalogManager
from album.core.controller.deploy_manager import DeployManager
from album.core.controller.install_manager import InstallManager
from album.core.controller.remove_manager import RemoveManager
from album.core.controller.resolve_manager import ResolveManager
from album.core.controller.run_manager import RunManager
from album.core.controller.search_manager import SearchManager
from album.core.controller.test_manager import TestManager
from album.core.model.catalog_collection import CatalogCollection
from album.core.model.configuration import Configuration
from album_runner import logging
from album_runner.logging import debug_settings

module_logger = logging.get_active_logger

# singletons initialization
configuration = Configuration()
catalog_collection = CatalogCollection(configuration)

# catalog_collection init
search_manager = SearchManager(catalog_collection)
resolve_manager = ResolveManager(catalog_collection)
catalog_manager = CatalogManager(catalog_collection)
deploy_manager = DeployManager(catalog_collection)

# resolve init
install_manager = InstallManager(resolve_manager)
remove_manager = RemoveManager(resolve_manager)
run_manager = RunManager(resolve_manager)
test_manager = TestManager(resolve_manager)


def startup():
    __retrieve_logger()
    module_logger().info(
        "Running album version %s \n \n %s - contact via %s " %
        (album.__version__, album.__author__, album.__email__))
    main()


def __retrieve_logger():
    """Retrieves the default album logger."""
    logging.configure_logging(logging.LogLevel(debug_settings()), 'album_core')


if __name__ == "__main__":
    startup()

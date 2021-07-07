import hips
from hips.argument_parsing import main
from hips.core.controller.catalog_manager import CatalogManager
from hips.core.controller.deploy_manager import DeployManager
from hips.core.controller.install_manager import InstallManager
from hips.core.controller.remove_manager import RemoveManager
from hips.core.controller.resolve_manager import ResolveManager
from hips.core.controller.run_manager import RunManager
from hips.core.controller.search_manager import SearchManager
from hips.core.controller.test_manager import TestManager
from hips.core.model.catalog_collection import HipsCatalogCollection
from hips.core.model.configuration import HipsConfiguration
from hips_runner import logging
from hips_runner.logging import hips_debug

module_logger = logging.get_active_logger

# singletons initialization
configuration = HipsConfiguration()
catalog_collection = HipsCatalogCollection(configuration)

# catalog_collection init
search_manager = SearchManager(catalog_collection)
resolve_manager = ResolveManager(catalog_collection)
hips_catalog_manager = CatalogManager(catalog_collection)
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
        (hips.__version__, hips.__author__, hips.__email__))
    main()


def __retrieve_logger():
    """Retrieves the default hips logger."""
    logging.configure_logging(logging.LogLevel(hips_debug()), 'hips_core')


if __name__ == "__main__":
    startup()

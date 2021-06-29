import sys

from hips.core import load
from hips.core.concept.singleton import Singleton
from hips.core.model.catalog_collection import HipsCatalogCollection
from hips.core.utils.operations.file_operations import copy_in_file
from hips.core.utils.script import create_script
from hips_runner import logging
from hips_runner.logging import LogLevel

module_logger = logging.get_active_logger


class InstallManager(metaclass=Singleton):
    """Class handling the installation process of a solution.

    During installation the conda environment (e.g. solutions target environment) the solution is supposed to
    be run in gets created and its dependencies installed. Additionally, the hips-runner will be added to the target
    environment. This lightweight program interprets the solution and runs the installation in the target environment.
    After installation the solution is marked as installed in a local catalog.

    Attributes:
        catalog_collection:
            Holding all configured catalogs.

    """
    # singletons
    catalog_collection = None

    def __init__(self, catalog_collection=None):
        self.catalog_collection = HipsCatalogCollection() if not catalog_collection else catalog_collection

    def install(self, path):
        """Function corresponding to the `install` subcommand of `hips`."""
        # Load HIPS
        resolve = self.catalog_collection.resolve_from_str(path)
        active_hips = load(resolve["path"])

        if not resolve["catalog"]:
            module_logger().debug('hips loaded locally: %s...' % str(active_hips))
        else:
            module_logger().debug('hips loaded from catalog %s: %s...' % (resolve["catalog"].id, str(active_hips)))

        # execute installation routine
        self._install(active_hips)

        if not resolve["catalog"] or resolve["catalog"].is_local:  # case where a solution file is directly given
            self.add_to_local_catalog(active_hips)

        module_logger().info('Installed %s!' % active_hips['name'])

    def add_to_local_catalog(self, active_hips):
        """Force adds the installation to the local catalog to be cached for running"""
        self.catalog_collection.local_catalog.add(active_hips, force_overwrite=True)
        local_catalog_path = self.catalog_collection.local_catalog.get_solution_cache_file(
            active_hips.group, active_hips.name, active_hips.version
        )
        copy_in_file(active_hips.script, local_catalog_path)

    def _install(self, active_hips):
        # install environment
        active_hips.environment.install(active_hips.min_hips_version)

        # install dependencies first. Recursive call to install with dependencies
        self.install_dependencies(active_hips)

        """Run install routine of hips if specified"""
        if active_hips['install'] and callable(active_hips['install']):
            module_logger().debug('Creating install script...')
            script = create_script(active_hips, "\nget_active_hips().install()\n", sys.argv)
            module_logger().debug('Calling install routine specified in solution...')
            logging.configure_logging(
                LogLevel(logging.to_loglevel(logging.get_loglevel_name())), active_hips['name']
            )
            active_hips.environment.run_scripts([script])
            logging.pop_active_logger()
        else:
            module_logger().warning(
                'No \"install\" routine configured for solution %s! Will install nothing...' % active_hips['name']
            )

    def install_dependencies(self, active_hips):
        """Handle dependencies in hips dependency block"""

        if active_hips.dependencies:  # todo: check if that is necessary any more
            if 'hips' in active_hips.dependencies:
                args = active_hips.dependencies['hips']
                for hips_dependency in args:
                    self.install_dependency(hips_dependency)

        if active_hips.parent:
            self.install_dependency(active_hips.parent)

    def install_dependency(self, hips_dependency):
        """Calls `install` for a HIPS declared in a dependency block"""
        hips_script_path = self.catalog_collection.resolve_hips_dependency(hips_dependency)["path"]
        # recursive installation call
        self.install(hips_script_path)

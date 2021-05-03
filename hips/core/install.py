import sys

from hips.core import load_and_push_hips, pop_active_hips
from hips.core.model import logging
from hips.core.model.configuration import HipsCatalogConfiguration
from hips.core.model.logging import LogLevel
from hips.core.utils.operations.file_operations import copy_in_file
from hips.core.utils.script import create_script

module_logger = logging.get_active_logger


def install(args):
    HipsInstaller().install(args)


class HipsInstaller:

    catalog_configuration = HipsCatalogConfiguration()
    active_hips = None

    def install(self, args):
        """Function corresponding to the `install` subcommand of `hips`."""
        # Load HIPS
        resolve = self.catalog_configuration.resolve_from_str(args.path)
        self.active_hips = load_and_push_hips(resolve["path"])

        if not resolve["catalog"]:
            module_logger().debug('hips loaded locally: %s...' % str(self.active_hips))
        else:
            module_logger().debug('hips loaded from catalog %s: %s...' % (resolve["catalog"].id, str(self.active_hips)))

        # install environment
        self.active_hips.environment.install(self.active_hips.min_hips_version)

        # install dependencies first. Recursive call to install with dependencies
        self.install_dependencies()

        # execute installation routine
        self.execute_install_routine()

        if not resolve["catalog"] or resolve["catalog"].is_local:  # case where a solution file is directly given
            self.add_to_local_catalog()

        module_logger().info('Installed %s!' % self.active_hips['name'])
        pop_active_hips()

    def add_to_local_catalog(self):
        """Force adds the installation to the local catalog to be cached for running"""
        self.catalog_configuration.local_catalog.add_to_index(self.active_hips, force_overwrite=True)
        local_catalog_path = self.catalog_configuration.local_catalog.get_solution_cache_file(
            self.active_hips.group, self.active_hips.name, self.active_hips.version
        )
        copy_in_file(self.active_hips.script, local_catalog_path)

    def execute_install_routine(self):
        """Run install routine of hips if specified"""
        if hasattr(self.active_hips, 'install') and callable(self.active_hips['install']):
            module_logger().debug('Creating install script...')
            script = create_script(self.active_hips, "\nget_active_hips().install()\n", sys.argv)
            module_logger().debug('Calling install routine specified in solution...')
            logging.configure_logging(
                LogLevel(logging.to_loglevel(logging.get_loglevel_name())), self.active_hips['name']
            )
            self.active_hips.run_script(script)
            logging.pop_active_logger()

    def install_dependencies(self):
        """Handle dependencies in hips dependency block"""

        if self.active_hips.dependencies:
            if 'hips' in self.active_hips.dependencies:
                args = self.active_hips.dependencies['hips']
                for hips_dependency in args:
                    self.install_dependency(hips_dependency)

        if self.active_hips.parent:
            self.install_dependency(self.active_hips.parent)

    def install_dependency(self, hips_dependency):
        """Calls `install` for a HIPS declared in a dependency block"""
        hips_script_path = self.catalog_configuration.resolve_hips_dependency(hips_dependency)["path"]
        # recursive installation call
        install(hips_script_path)


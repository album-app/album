import sys

import hips
from utils import subcommand, hips_logging
from utils.environment import create_or_update_environment, run_in_environment
from utils.hips_resolve import resolve_hips
from utils.hips_script import create_script

module_logger = hips_logging.get_active_logger


def install(args):
    """Function corresponding to the `install` subcommand of `hips`."""
    # Load HIPS
    active_hips = hips.load_and_push_hips(args.path)

    module_logger().debug('hips loaded locally: %s' % str(active_hips))

    create_or_update_environment(active_hips)
    __handle_dependencies(active_hips)
    __handle_parent(active_hips)
    __execute_install_routine(active_hips)

    # ToDo: install helper - methods (pip install) (git-download) (java-dependcies)

    module_logger().info('Installed %s' % active_hips['name'])
    hips.pop_active_hips()


def __execute_install_routine(active_hips):
    """Run install routine of hips if specified"""
    if hasattr(active_hips, 'install') and callable(active_hips['install']):
        module_logger().debug('Calling install routine specified in solution...')
        script = create_script(active_hips, "\nhips.get_active_hips().install()\n", sys.argv)
        run_in_environment(active_hips["_environment_path"], script)


def __handle_dependencies(active_hips):
    """Handle dependencies in hips dependency block"""
    if 'dependencies' in dir(active_hips):
        dependencies = active_hips['dependencies']
        if 'hips' in dependencies:
            args = dependencies['hips']
            for hips_dependency in args:
                __install_hips(hips_dependency)


def __install_hips(hips_dependency):
    """Calls `install` for a HIPS declared in a dependency block"""
    hips_script = resolve_hips(hips_dependency)
    subcommand.run("python -m hips install " + hips_script)


def __handle_parent(active_hips):
    """Handle parent of hips"""
    if 'parent' in dir(active_hips):
        parent = active_hips['parent']
        __install_hips(parent)

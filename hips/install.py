import logging

import hips
from utils import subcommand
from utils.environment import create_or_update_environment, run_in_environment
from utils.hips_resolve import resolve_hips
from utils.hips_script import create_script

module_logger = logging.getLogger('hips')


def install(args):
    """Function corresponding to the `install` subcommand of `hips`."""
    # Load HIPS
    hips.load_and_push_hips(args.path)
    active_hips = hips.get_active_hips()

    module_logger.debug('hips loaded locally: %s' % str(active_hips))

    create_or_update_environment(active_hips)
    __handle_dependencies(active_hips)
    __execute_install_routine(active_hips)

    # ToDo: install helper - methods (pip install) (git-download) (java-dependcies)

    module_logger.info('Installed %s' % active_hips['name'])
    hips.pop_active_hips()


def __execute_install_routine(active_hips):
    """Run install routine of hips if specified"""
    if hasattr(active_hips, 'install') and callable(active_hips['install']):
        module_logger.debug('Calling install routine specified in solution...')
        script = create_script(active_hips, "\nhips.get_active_hips().install()\n")
        run_in_environment(active_hips, script)


def __handle_dependencies(active_hips):
    """Handle dependencies in hips dependency block"""
    if 'dependencies' in dir(active_hips):
        dependencies = active_hips['dependencies']
        if 'hips' in dependencies:
            __install_hips_dependencies(dependencies['hips'])


def __install_hips_dependencies(args):
    """Calls `install` for all hips declared in a dependency block"""
    for hips_dependency in args:
        hips_script = resolve_hips(hips_dependency)
        subcommand.run("python -m hips install " + hips_script)


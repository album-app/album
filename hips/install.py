import sys

import hips
from hips_utils import subcommand, hips_logging
from hips_utils.environment import create_or_update_environment, run_in_environment
from hips_utils.hips_resolve import resolve_hips, resolve_from_str, get_configuration
from hips_utils.hips_script import create_script

module_logger = hips_logging.get_active_logger


def install(args):
    """Function corresponding to the `install` subcommand of `hips`."""
    # Load HIPS
    resolve = resolve_from_str(args.path)
    active_hips = hips.load_and_push_hips(resolve["path"])

    if not resolve["catalog"]:
        module_logger().debug('hips loaded locally: %s' % str(active_hips))
    else:
        module_logger().debug('hips loaded from catalog %s: %s' % (resolve["catalog"].id, str(active_hips)))

    create_or_update_environment(active_hips)
    __handle_dependencies(active_hips)
    __handle_parent(active_hips)
    __execute_install_routine(active_hips)
    if not resolve["catalog"]:
        __add_to_local_catalog(active_hips)

    module_logger().info('Installed %s' % active_hips['name'])
    hips.pop_active_hips()


def __add_to_local_catalog(active_hips):
    """Force adds the installation to the local catalog to be cached for running"""
    hips_config = get_configuration()
    hips_config.local_catalog.add_to_index(active_hips, force_overwrite=True)


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
    hips_script = resolve_hips(hips_dependency)["path"]
    # todo: why don't we call "install" directly? Why a new process?
    subcommand.run("python -m hips install " + hips_script + " --log=%s" % hips_logging.LogLevel(hips.hips_debug()).name)


def __handle_parent(active_hips):
    """Handle parent of hips"""
    if 'parent' in dir(active_hips):
        parent = active_hips['parent']
        __install_hips(parent)

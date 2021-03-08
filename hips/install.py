from hips import Hips, get_active_hips
from utils import subcommand
import logging


module_logger = logging.getLogger('hips')


def install(args):
    """Function corresponding to the `install` subcommand of `hips`."""
    # Load HIPS
    __load_script(args.path)
    __handle_dependencies(get_active_hips())
    __execute_install_routine(get_active_hips())

    # ToDo: install helper - methods (pip install) (git-download) (java-dependcies)

    module_logger.info('Installed %s' % get_active_hips()['name'])


def __load_script(path):
    """Load hips script"""
    hips_script = open(path).read()
    exec(hips_script)


def __execute_install_routine(active_hips):
    """Run install routine of hips if specified"""
    if hasattr(active_hips, 'install') and callable(active_hips['install']):
        module_logger.debug('Calling install routine specified in solution...')
        active_hips.install()


def __handle_dependencies(active_hips):
    """Handle dependencies in hips dependency block"""
    if 'dependencies' in dir():
        dependencies = active_hips['dependencies']
        if 'hips' in dependencies:
            __install_hips_dependencies(dependencies['hips'])


def __install_hips_dependencies(args):
    """Calls `install` for all hips declared in a dependency block"""
    for hips in args:
        hips_script = __resolve_hips(hips)
        subcommand.run_string("python -m hips install " + hips_script)


def __resolve_hips(hips):
    """Resolves a hips id and returns a path to the solution file."""
    # TODO properly implement this - i.e. match with zenodo
    path = ""
    if hips["group"] == "ida-mdc" and hips["name"] == "blender":
        path = "./examples/blender.py"
    return path


from hips import Hips, get_active_hips
from utils import subcommand
import logging


module_logger = logging.getLogger('hips')


def install(args):
    """Function corresponding to the `install` subcommand of `hips`."""
    # Load HIPS
    hips_script = open(args.path).read()
    exec(hips_script)
    hips = get_active_hips()
    if 'dependencies' in dir(hips):
        dependencies = hips['dependencies']
        if 'hips' in dependencies:
            __install_hips_dependencies(dependencies['hips'])

    # execute install routine
    if hasattr(get_active_hips(), 'install') and callable(get_active_hips()['install']):
        module_logger.debug('Calling install routine specified in solution...')
        get_active_hips().install()

    # ToDo: install helper - methods (pip install) (git-download) (java-dependcies)

    module_logger.info('Installed %s' % hips['name'])


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


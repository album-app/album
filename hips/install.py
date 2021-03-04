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
            install_hips_dependencies(dependencies['hips'])

    # execute install routine
    if hasattr(get_active_hips(), 'install') and callable(get_active_hips()['install']):
        module_logger.debug('Calling install routine specified in solution...')
        get_active_hips().install()

    # ToDo: install helper - methods (pip install) (git-download) (java-dependcies)

    module_logger.info('Installed %s' % hips['name'])


def install_hips_dependencies(args):
    for hips in args:
        hips_script = resolve_hips(hips)
        subcommand.run("python -m hips install " + hips_script)


def resolve_hips(hips):
    # TODO properly implement this - i.e. match with zenodo
    path = ""
    if hips["group"] == "ida-mdc" and hips["name"] == "blender":
        path = "./examples/blender.py"
    return path


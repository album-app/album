from hips.core import load_and_push_hips, pop_active_hips, get_active_hips
from hips.core.controller.catalog_manager import CatalogManager
from hips.core.controller.deploy_manager import DeployManager
from hips.core.controller.install_manager import InstallManager
from hips.core.controller.remove_manager import RemoveManager
from hips.core.controller.run_manager import RunManager
from hips.core.controller.search_manager import SearchManager
from hips.core.server import HipsServer
from hips.core.controller.test_manager import TestManager
from hips_runner import logging
from hips_runner.logging import hips_debug

module_logger = logging.get_active_logger

# NOTE: Singleton instances should already be initialized at this point! Look at __main__.py!
# Calling Singleton classes only gives back the already initialized instances!

# ToDo: environment purge method
# ToDo: reusable versioned environments?
# ToDo: test for windows
# ToDo: subprocess logging (https://www.endpoint.com/blog/2015/01/28/getting-realtime-output-using-python)


def add_catalog(args):
    CatalogManager().add(args.path)


def remove_catalog(args):
    CatalogManager().remove(args.path)


def deploy(args):
    DeployManager().deploy(args.path, args.catalog, args.dry_run, args.trigger_pipeline, args.git_email, args.git_name)


def install(args):
    InstallManager().install(args.path)


def remove(args):
    RemoveManager().remove(args.path, args.remove_deps)


def run(args):
    RunManager().run(args.path, args.run_immediately)


def search(args):
    SearchManager().search(args.keywords)


def start_server(args):
    HipsServer(args.port).start()


def test(args):
    TestManager().test(args.path)


def tutorial(args):
    """Function corresponding to the `tutorial` subcommand of `hips`."""
    active_hips = load_and_push_hips(args.path)
    module_logger().info('This would run a tutorial for: %s...' % active_hips['name'])
    pop_active_hips()


def containerize(args):
    """Function corresponding to the `containerize` subcommand of `hips`."""
    # Load HIPS
    active_hips = load_and_push_hips(args.path)
    module_logger().info('This would containerize: %s...' % active_hips['name'])
    pop_active_hips()


def repl(args):
    """Function corresponding to the `repl` subcommand of `hips`."""
    # Load HIPS
    hips_script = open(args.path).read()
    exec(hips_script)

    hips = get_active_hips()

    if hips_debug():
        module_logger().debug('hips loaded locally: %s...' % str(hips))

    # Get environment name
    environment_name = hips.environment_name

    script = """from code import InteractiveConsole
"""

    script += hips_script

    # Create an interactive console with our globals and locals
    script += """
console = InteractiveConsole(locals={
    **globals(),
    **locals()
},
                             filename="<console>")
console.interact()
"""
    hips.run_scripts(script)

from album.core.controller.catalog_manager import CatalogManager

from album.core import load_and_push_solution, pop_active_solution, get_active_solution
from album.core.controller.deploy_manager import DeployManager
from album.core.controller.install_manager import InstallManager
from album.core.controller.remove_manager import RemoveManager
from album.core.controller.run_manager import RunManager
from album.core.controller.search_manager import SearchManager
from album.core.controller.test_manager import TestManager
from album.core.server import AlbumServer
from album_runner import logging
from album_runner.logging import debug_settings

module_logger = logging.get_active_logger

# NOTE: Calling Singleton classes gives back the already initialized instances only!


def add_catalog(args):
    CatalogManager().add(args.path)


def remove_catalog(args):
    CatalogManager().remove(args.path)


def update(args):
    CatalogManager().update_any(args.catalog_id)


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
    AlbumServer(args.port).start()


def test(args):
    TestManager().test(args.path)


def repl(args):
    """Function corresponding to the `repl` subcommand of `album`."""
    # Load solution
    solution_script = open(args.path).read()
    exec(solution_script)

    solution = get_active_solution()

    if debug_settings():
        module_logger().debug('album loaded locally: %s...' % str(solution))

    # Get environment name
    environment_name = solution.environment_name

    script = """from code import InteractiveConsole
"""

    script += solution_script

    # Create an interactive console with our globals and locals
    script += """
console = InteractiveConsole(locals={
    **globals(),
    **locals()
},
                             filename="<console>")
console.interact()
"""
    solution.run_scripts(script)

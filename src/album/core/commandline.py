import json
import sys

from album.core import get_active_solution
from album.core.controller.clone_manager import CloneManager
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.controller.deploy_manager import DeployManager
from album.core.controller.install_manager import InstallManager
from album.core.controller.run_manager import RunManager
from album.core.controller.search_manager import SearchManager
from album.core.controller.test_manager import TestManager
from album.core.server import AlbumServer
from album.runner import logging
from album.runner.logging import debug_settings

module_logger = logging.get_active_logger


# NOTE: Calling Singleton classes gives back the already initialized instances only!


def add_catalog(args):
    CollectionManager().catalogs().add_by_src(args.src)


def remove_catalog(args):
    CollectionManager().catalogs().remove_from_collection_by_src(args.src)


# todo: do argument parsing properly
def update(args):
    CollectionManager().catalogs().update_any(getattr(args, "catalog_name", None))


# todo: do argument parsing properly
def upgrade(args):
    dry_run = getattr(args, "dry_run", False)
    updates = CollectionManager().catalogs().update_collection(getattr(args, "catalog_name", None),
                                                               dry_run=dry_run)
    if dry_run:
        module_logger().info("An upgrade would apply the following updates:")
    else:
        module_logger().info("Applied the following updates:")
    for change in updates:
        module_logger().info(json.dumps(change.as_dict(), sort_keys=True, indent=4))


def deploy(args):
    DeployManager().deploy(
        args.path, args.catalog, args.dry_run, args.push_option, args.git_email, args.git_name, args.force_deploy
    )


def install(args):
    InstallManager().install(args.path, sys.argv)


def uninstall(args):
    InstallManager().uninstall(args.path, args.uninstall_deps)


def run(args):
    RunManager().run(args.path, args.run_immediately, sys.argv)


def search(args):
    SearchManager().search(args.keywords)


def start_server(args):
    server = AlbumServer(args.port, args.host)
    server.setup()
    server.start()


def test(args):
    TestManager().test(args.path, sys.argv)


def clone(args):
    CloneManager().clone(args.src, args.target_dir, args.name)


def index(args):
    module_logger().info(json.dumps(CollectionManager().get_index_as_dict(), sort_keys=True, indent=4))


def repl(args):
    """Function corresponding to the `repl` subcommand of `album`."""
    # this loads a solution, opens python session in terminal, and lets you run python commands in the environment of the solution
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

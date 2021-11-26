import sys

from album.api import Album
from album.core.controller.clone_manager import CloneManager
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.controller.deploy_manager import DeployManager
from album.core.controller.install_manager import InstallManager
from album.core.controller.run_manager import RunManager
from album.core.controller.search_manager import SearchManager
from album.core.controller.test_manager import TestManager
from album.core.server import AlbumServer
from album.core.utils.operations.solution_operations import get_deploy_dict, serialize_json
from album.core.utils.operations.view_operations import get_solution_as_string, \
    get_updates_as_string, get_index_as_string, get_search_result_as_string
from album.runner.album_logging import get_active_logger

module_logger = get_active_logger


def add_catalog(args) -> None:
    CollectionManager().catalogs().add_by_src(args.src)


def remove_catalog(args) -> None:
    CollectionManager().catalogs().remove_from_collection_by_src(args.src)


def update(args):
    CollectionManager().catalogs().update_any(getattr(args, "catalog_name", None))


def upgrade(args):
    dry_run = getattr(args, "dry_run", False)
    updates = CollectionManager().catalogs().update_collection(getattr(args, "catalog_name", None),
                                                               dry_run=dry_run)
    print_json = _get_print_json(args)
    if print_json:
        print(_as_json(updates))
    else:
        res = ''
        if dry_run:
            res += 'An upgrade would apply the following updates:\n'
        else:
            res += "Applied the following updates:\n"
        res += get_updates_as_string(updates)
        module_logger().info(res)


def deploy(args):
    DeployManager().deploy(
        args.path, args.catalog, args.dry_run, args.push_option, args.git_email, args.git_name, args.force_deploy, args.changelog
    )


def install(args):
    InstallManager().install(args.path, sys.argv)


def uninstall(args):
    InstallManager().uninstall(args.path, args.uninstall_deps, sys.argv)


def info(args):
    solution_path = args.path
    resolve_result = CollectionManager().resolve_download_and_load(str(solution_path))
    print_json = _get_print_json(args)
    solution = resolve_result.loaded_solution
    if print_json:
        deploy_dict = get_deploy_dict(solution)
        print(_as_json(deploy_dict))
    else:
        res = get_solution_as_string(solution, solution_path)
        module_logger().info(res)


def run(args):
    RunManager().run(args.path, args.run_immediately, sys.argv)


def search(args):
    print_json = _get_print_json(args)
    search_result = SearchManager().search(args.keywords)
    if print_json:
        print(_as_json(search_result))
    else:
        res = get_search_result_as_string(args, search_result)
        module_logger().info(res)


def start_server(args):
    server = AlbumServer(args.port, args.host)
    server.setup(Album())
    server.start()


def test(args):
    TestManager().test(args.path, sys.argv)


def clone(args):
    CloneManager().clone(args.src, args.target_dir, args.name)


def index(args):
    index_dict = CollectionManager().get_index_as_dict()
    print_json = _get_print_json(args)
    if print_json:
        print(_as_json(index_dict))
    else:
        res = get_index_as_string(index_dict)
        module_logger().info('Catalogs in your local collection: %s' % res)


def repl(args):
    """Function corresponding to the `repl` subcommand of `album`."""
    module_logger().info("This feature will be available soon!")
    # this loads a solution, opens python session in terminal, and lets you run python commands in the environment of the solution
    # Load solution


def _get_print_json(args):
    return getattr(args, "json", False)


def _as_json(data):
    return serialize_json(data)


#     solution_script = open(args.path).read()
#     exec(solution_script)
#
#     solution = get_active_solution()
#
#     if debug_settings():
#         module_logger().debug('album loaded locally: %s...' % str(solution))
#
#     # Get environment name
#     environment_name = solution.environment_name
#
#     script = """from code import InteractiveConsole
# """
#
#     script += solution_script
#
#     # Create an interactive console with our globals and locals
#     script += """
# console = InteractiveConsole(locals={
#     **globals(),
#     **locals()
# },
#                              filename="<console>")
# console.interact()
# """
#     solution.run_scripts(script)

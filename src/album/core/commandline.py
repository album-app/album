import sys
from queue import Queue

from album.core.api.album import IAlbum
from album.core.server import AlbumServer
from album.core.utils.operations.solution_operations import get_deploy_dict, serialize_json
from album.core.utils.operations.view_operations import get_solution_as_string, \
    get_updates_as_string, get_index_as_string, get_search_result_as_string
from album.runner.album_logging import get_active_logger
from album.runner.core.api.model.solution import ISolution
from album.runner.core.model.script_creator import ScriptCreatorRun

module_logger = get_active_logger


def add_catalog(album_instance: IAlbum, args) -> None:
    album_instance.collection_manager().catalogs().add_by_src(args.src)


def remove_catalog(album_instance: IAlbum, args) -> None:
    album_instance.collection_manager().catalogs().remove_from_collection_by_src(args.src)


def update(album_instance: IAlbum, args):
    album_instance.collection_manager().catalogs().update_any(getattr(args, "catalog_name", None))


def upgrade(album_instance: IAlbum, args):
    dry_run = getattr(args, "dry_run", False)
    updates = album_instance.collection_manager().catalogs().update_collection(getattr(args, "catalog_name", None),
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


def deploy(album_instance: IAlbum, args):
    album_instance.deploy_manager().deploy(
        args.path, args.catalog, args.dry_run, args.push_option, args.git_email, args.git_name, args.force_deploy,
        args.changelog
    )


def install(album_instance: IAlbum, args):
    album_instance.install_manager().install(args.path, sys.argv)


def uninstall(album_instance: IAlbum, args):
    album_instance.install_manager().uninstall(args.path, args.uninstall_deps, sys.argv)


def info(album_instance: IAlbum, args):
    solution_path = args.path
    resolve_result = album_instance.collection_manager().resolve_download_and_load(str(solution_path))
    print_json = _get_print_json(args)
    solution = resolve_result.loaded_solution()
    if print_json:
        deploy_dict = get_deploy_dict(solution)
        print(_as_json(deploy_dict))
    else:
        res = get_solution_as_string(solution, solution_path)
        module_logger().info(res)


def run(album_instance: IAlbum, args):
    album_instance.run_manager().run(args.path, args.run_immediately, sys.argv)


def search(album_instance: IAlbum, args):
    print_json = _get_print_json(args)
    search_result = album_instance.search_manager().search(args.keywords)
    if print_json:
        print(_as_json(search_result))
    else:
        res = get_search_result_as_string(args, search_result)
        module_logger().info(res)


def start_server(album_instance: IAlbum, args):
    server = AlbumServer(args.port, args.host)
    server.setup(album_instance)
    server.start()


def test(album_instance: IAlbum, args):
    album_instance.test_manager().test(args.path, sys.argv)


def clone(album_instance: IAlbum, args):
    album_instance.clone_manager().clone(args.src, args.target_dir, args.name)


def index(album_instance: IAlbum, args):
    index_dict = album_instance.collection_manager().get_index_as_dict()
    print_json = _get_print_json(args)
    if print_json:
        print(_as_json(index_dict))
    else:
        res = get_index_as_string(index_dict)
        module_logger().info('Catalogs in your local collection: %s' % res)


def repl(album_instance: IAlbum, args):
    """Function corresponding to the `repl` subcommand of `album`."""
    # resolve the input
    resolve_result = album_instance.collection_manager().resolve_require_installation_and_load(args.path)
    queue = Queue()
    script_creator = ScriptRepl()
    album_instance.run_manager().build_queue(resolve_result.loaded_solution(), resolve_result.catalog(), queue,
                                             script_creator, False, [""])
    script_queue_entry = queue.get(block=False)
    album_instance.environment_manager().get_conda_manager().run_scripts(script_queue_entry.environment,
                                                                         script_queue_entry.scripts, pipe_output=False)
    module_logger().info('Ran REPL for \"%s\"!' % resolve_result.loaded_solution().coordinates().name())


def _get_print_json(args):
    return getattr(args, "json", False)


def _as_json(data):
    return serialize_json(data)


class ScriptRepl(ScriptCreatorRun):
    def get_execution_block(self, solution_object: ISolution):
        return """
from code import InteractiveConsole
try:
    import readline
except ImportError:
    print("Module readline not available.")
else:
    import rlcompleter
    readline.parse_and_bind("tab: complete")
console = InteractiveConsole(locals={**globals(), **locals()})
console.interact()
"""

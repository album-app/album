import sys

from album.api import Album
from album.core.utils.operations.solution_operations import get_deploy_dict, serialize_json
from album.core.utils.operations.view_operations import get_solution_as_string, \
    get_updates_as_string, get_index_as_string, get_search_result_as_string
from album.runner.album_logging import get_active_logger
from album.runner.core.api.model.solution import ISolution
from album.runner.core.model.script_creator import ScriptCreatorRun
from album.server import AlbumServer

module_logger = get_active_logger


def add_catalog(album_instance: Album, args) -> None:
    album_instance.add_catalog(args.src)


def remove_catalog(album_instance: Album, args) -> None:
    album_instance.remove_catalog_by_src(args.src)


def update(album_instance: Album, args):
    album_instance.update(getattr(args, "catalog_name", None))


def upgrade(album_instance: Album, args):
    dry_run = getattr(args, "dry_run", False)
    updates = album_instance.upgrade(getattr(args, "catalog_name", None), dry_run=dry_run)
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


def deploy(album_instance: Album, args):
    album_instance.deploy(
        args.path, args.catalog, args.dry_run, args.push_option, args.git_email, args.git_name, args.force_deploy,
        args.changelog
    )


def install(album_instance: Album, args):
    album_instance.install(_resolve(album_instance, args.path), sys.argv)


def uninstall(album_instance: Album, args):
    album_instance.uninstall(_resolve_installed(album_instance, args.path), args.uninstall_deps, sys.argv)


def info(album_instance: Album, args):
    solution_path = args.path
    resolve_result = _resolve(album_instance, args.path)
    print_json = _get_print_json(args)
    solution = resolve_result.loaded_solution()
    if print_json:
        deploy_dict = get_deploy_dict(solution)
        print(_as_json(deploy_dict))
    else:
        res = get_solution_as_string(solution, solution_path)
        module_logger().info(res)


def run(album_instance: Album, args):
    album_instance.run(_resolve_installed(album_instance, args.path), argv=sys.argv, run_immediately=args.run_immediately)


def search(album_instance: Album, args):
    print_json = _get_print_json(args)
    search_result = album_instance.search(args.keywords)
    if print_json:
        print(_as_json(search_result))
    else:
        res = get_search_result_as_string(args, search_result)
        module_logger().info(res)


def start_server(album_instance: Album, args):
    server = AlbumServer(args.port, args.host)
    server.setup(album_instance)
    server.start()


def test(album_instance: Album, args):
    album_instance.test(_resolve_installed(album_instance, args.path), sys.argv)


def clone(album_instance: Album, args):
    album_instance.clone(args.src, args.target_dir, args.name)


def index(album_instance: Album, args):
    index_dict = album_instance.get_index_as_dict()
    print_json = _get_print_json(args)
    if print_json:
        print(_as_json(index_dict))
    else:
        res = get_index_as_string(index_dict)
        module_logger().info('Catalogs in your local collection: %s' % res)


def repl(album_instance: Album, args):
    """Function corresponding to the `repl` subcommand of `album`."""
    # resolve the input
    resolve_result = _resolve_installed(album_instance, args.path)
    album_instance.run_solution_script(resolve_result, ScriptRepl())
    module_logger().info('Ran REPL for \"%s\"!' % resolve_result.loaded_solution().coordinates().name())


def _resolve(album_instance: Album, solution_resolve: str):
    return album_instance.resolve(str(solution_resolve))


def _resolve_installed(album_instance: Album, solution_resolve: str):
    return album_instance.resolve_installed(str(solution_resolve))


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

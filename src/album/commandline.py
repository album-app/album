"""Module containing the commandline functions for the `album` commandline tool."""
import os
import pkgutil
import sys
import tempfile
from argparse import Namespace

from album.api import Album
from album.core.utils.operations.solution_operations import (
    get_deploy_dict,
    serialize_json,
)
from album.core.utils.operations.view_operations import (
    get_index_as_string,
    get_search_result_as_string,
    get_solution_as_string,
    get_updates_as_string,
)
from album.runner.album_logging import get_active_logger
from album.runner.core.model.solution import Solution

module_logger = get_active_logger


def add_catalog(album_instance: Album, args: Namespace) -> None:
    """Call function corresponding to the `add-catalog` subcommand of `album`."""
    album_instance.add_catalog(args.src)


def remove_catalog(album_instance: Album, args: Namespace) -> None:
    """Call function corresponding to the `remove-catalog` subcommand of `album`."""
    album_instance.remove_catalog_by_name(args.name)


def update(album_instance: Album, args: Namespace):
    """Call function corresponding to the `update` subcommand of `album`."""
    album_instance.update(getattr(args, "catalog", None))


def upgrade(album_instance: Album, args: Namespace):
    """Call function corresponding to the `upgrade` subcommand of `album`."""
    updates = album_instance.upgrade(
        getattr(args, "catalog", None), dry_run=args.dry_run, override=args.override
    )
    print_json = _get_print_json(args)
    if print_json:
        print(_as_json(updates))
    else:
        res = ""
        if args.dry_run:
            res += "An upgrade would apply the following updates:\n"
        else:
            res += "Applied the following updates:\n"
        res += get_updates_as_string(updates)
        module_logger().info(res)


def deploy(album_instance: Album, args: Namespace):
    """Call function corresponding to the `deploy` subcommand of `album`."""
    album_instance.deploy(
        args.path,
        args.catalog,
        args.dry_run,
        args.push_option,
        args.git_email,
        args.git_name,
        args.force_deploy,
        args.changelog,
        args.no_conda_lock,
    )


def undeploy(album_instance: Album, args: Namespace):
    """Call function corresponding to the `undeploy` subcommand of `album`."""
    album_instance.undeploy(
        args.path,
        args.catalog,
        args.dry_run,
        args.push_option,
        args.git_email,
        args.git_name,
    )


def install(album_instance: Album, args: Namespace):
    """Call function corresponding to the `install` subcommand of `album`."""
    album_instance.install(str(args.path), args.allow_recursive, sys.argv)


def uninstall(album_instance: Album, args: Namespace):
    """Call function corresponding to the `uninstall` subcommand of `album`."""
    album_instance.uninstall(str(args.path), args.uninstall_deps, sys.argv)


def info(album_instance: Album, args: Namespace):
    """Call function corresponding to the `info` subcommand of `album`."""
    solution_path = args.path
    resolve_result = album_instance.resolve(str(args.path))
    print_json = _get_print_json(args)
    solution = resolve_result.loaded_solution()
    if print_json:
        deploy_dict = get_deploy_dict(solution)
        print(_as_json(deploy_dict))
    else:
        res = get_solution_as_string(solution, solution_path)
        module_logger().info(res)


def run(album_instance: Album, args: Namespace):
    """Call function corresponding to the `run` subcommand of `album`."""
    album_instance.run(str(args.path), argv=sys.argv)


def search(album_instance: Album, args: Namespace):
    """Call function corresponding to the `search` subcommand of `album`."""
    print_json = _get_print_json(args)
    search_result = album_instance.search(args.keywords)
    if print_json:
        print(_as_json(search_result))
    else:
        res = get_search_result_as_string(args, search_result)
        module_logger().info(res)


def test(album_instance: Album, args: Namespace):
    """Call function corresponding to the `test` subcommand of `album`."""
    album_instance.test(str(args.path), sys.argv)


def clone(album_instance: Album, args: Namespace):
    """Call function corresponding to the `clone` subcommand of `album`."""
    album_instance.clone(args.src, args.target_dir, args.name)


def index(album_instance: Album, args: Namespace):
    """Call function corresponding to the `index` subcommand of `album`."""
    index_dict = album_instance.get_index_as_dict()
    print_json = _get_print_json(args)
    if print_json:
        print(_as_json(index_dict))
    else:
        res = get_index_as_string(index_dict)
        module_logger().info(res)


def _merge_scripts(script1, script2_content, tmp_dir):
    """Merge two scripts into one."""
    with open(script1) as fp:
        data = fp.read()

    data += "\n"
    data += script2_content.decode("utf-8")

    with tempfile.NamedTemporaryFile(
        "w", suffix=".py", prefix="solution_repl", dir=tmp_dir, delete=False
    ) as tmp_file:
        tmp_file.write(data)
    return tmp_file.name


def repl(album_instance: Album, args: Namespace):
    """Call function corresponding to the `repl` subcommand of `album`."""
    # resolve the input
    resolve_result = album_instance.resolve_installed(str(args.path))
    solution_script = resolve_result.loaded_solution().script()
    repl_script_content = pkgutil.get_data("album.core.utils.runner", "repl.py")
    script = _merge_scripts(
        solution_script, repl_script_content, album_instance.configuration().tmp_path()
    )
    resolve_result.loaded_solution().set_script(script)
    album_instance.run_solution_script(resolve_result, Solution.Action.NO_ACTION)
    os.remove(script)
    module_logger().info(
        'Ran REPL for "%s"!' % resolve_result.loaded_solution().coordinates().name()
    )


def _get_print_json(args):
    """Check if the user wants to print the output as JSON."""
    return getattr(args, "json", False)


def _as_json(data):
    """Serialize data as JSON."""
    return serialize_json(data)

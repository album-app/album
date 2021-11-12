import json
import sys

from album.core.utils.operations.solution_operations import get_deploy_dict, serialize_json
from album.runner.album_logging import get_active_logger

from album.api import Album
from album.core.controller.clone_manager import CloneManager
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.controller.deploy_manager import DeployManager
from album.core.controller.install_manager import InstallManager
from album.core.controller.run_manager import RunManager
from album.core.controller.search_manager import SearchManager
from album.core.controller.test_manager import TestManager
from album.core.server import AlbumServer

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
        for change in updates:
            res += 'Catalog: %s\n' % change.catalog.name
            if len(change.catalog_attribute_changes) > 0:
                res += '  Catalog attribute changes:\n'
                for item in change.catalog_attribute_changes:
                    res += '  name: %s, new value: %s\n' % (item.attribute, item.new_value)
            if len(change.solution_changes) > 0:
                res += '  Catalog solution changes:\n'
                for i, item in enumerate(change.solution_changes):
                    if i is len(change.solution_changes) - 1:
                        res += '  └─ [%s] %s\n' % (item.change_type.name, item.coordinates)
                        separator = ' '
                    else:
                        res += '  ├─ [%s] %s\n' % (item.change_type.name, item.coordinates)
                        separator = '|'
                    res += '  %s     %schangelog: %s\n' % (
                        separator, (" " * len(item.change_type.name)), item.change_log)

            if len(change.catalog_attribute_changes) == 0 and len(change.solution_changes) == 0:
                res += '  No changes.\n'
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
    resolve_result = CollectionManager().resolve_download_and_load(str(args.path))
    print_json = _get_print_json(args)
    solution = resolve_result.loaded_solution
    deploy_dict = get_deploy_dict(solution)
    if print_json:
        print(_as_json(deploy_dict))
    else:
        param_example_str = ''
        for arg in deploy_dict['args']:
            param_example_str += '--%s PARAMETER_VALUE ' % arg['name']
        res = 'Solution details about %s:\n\n' % args.path
        if solution.setup.title:
            res += '%s\n' % solution.setup.title
            res += '%s\n' % ('=' * len(solution.setup.title))
        if solution.setup.description:
            res += '%s\n\n' % solution.setup.description
        res += 'Group            : %s\n' % solution.setup.group
        res += 'Name             : %s\n' % solution.setup.name
        res += 'Version          : %s' % solution.setup.version
        res += '%s' % get_credit_as_string(solution)
        res += 'Solution metadata:\n\n'
        if solution.setup.authors:
            res += 'Solution authors : %s\n' % ", ".join(solution.setup.authors)
        if solution.setup.license:
            res += 'License          : %s\n' % solution.setup.license
        if solution.setup.acknowledgement:
            res += 'Acknowledgement  : %s\n' % solution.setup.acknowledgement
        if solution.setup.tags:
            res += 'Tags             : %s\n' % ", ".join(solution.setup.tags)
        res += '\n'
        res += 'Usage:\n\n'
        res += '  album install %s\n' % args.path
        res += '  album run %s %s\n' % (solution.coordinates, param_example_str)
        res += '  album test %s\n' % solution.coordinates
        res += '  album uninstall %s\n' % solution.coordinates
        res += '\n'
        res += 'Run parameters:\n\n'
        for arg in deploy_dict['args']:
            res += '  --%s: %s\n' % (arg["name"], arg["description"])
        module_logger().info(res)


def run(args):
    RunManager().run(args.path, args.run_immediately, sys.argv)


def search(args):
    print_json = _get_print_json(args)
    search_result = SearchManager().search(args.keywords)
    if print_json:
        print(_as_json(search_result))
    else:
        res = ''
        if len(search_result) > 0:
            res += 'Search results for "%s" - run `album info SOLUTION_ID` for more information:\n' % ' '.join(
                args.keywords)
            res += '[SCORE] SOLUTION_ID\n'
            for result in search_result:
                res += '[%s] %s\n' % (result[1], result[0])
        else:
            res += 'No search results for "%s".' % ' '.join(args.keywords)
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
        res = '\n'
        if 'catalogs' in index_dict:
            for catalog in index_dict['catalogs']:
                res += 'Catalog \'%s\':\n' % catalog['name']
                res += '├─ name: %s\n' % catalog['name']
                res += '├─ src: %s\n' % catalog['src']
                res += '├─ catalog_id: %s\n' % catalog['catalog_id']
                if len(catalog['solutions']) > 0:
                    res += '├─ deletable: %s\n' % catalog['deletable']
                    res += '└─ solutions:\n'
                    for i, solution in enumerate(catalog['solutions']):
                        if i is len(catalog['solutions']) - 1:
                            res += '   └─ %s:%s:%s\n' % (solution.setup['group'], solution.setup['name'], solution.setup['version'])
                        else:
                            res += '   ├─ %s:%s:%s\n' % (solution.setup['group'], solution.setup['name'], solution.setup['version'])
                else:
                    res += '└─ deletable: %s\n' % catalog['deletable']
        module_logger().info('Catalogs in your local collection: %s' % res)


def repl(args):
    """Function corresponding to the `repl` subcommand of `album`."""
    module_logger().info("This feature will be available soon!")
    # this loads a solution, opens python session in terminal, and lets you run python commands in the environment of the solution
    # Load solution


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


def _get_print_json(args):
    return getattr(args, "json", False)


def _as_json(data):
    return serialize_json(data)


def get_credit_as_string(solution):
    res = ''
    if solution.setup.cite:
        res += '\n\nCredits:\n\n'
        for citation in solution.setup.cite:
            text = citation['text']
            if 'doi' in citation:
                text += ' (DOI: %s)' % citation['doi']
            res += '%s\n' % text
        res += '\n'
    return res
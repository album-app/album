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
from album.runner.logging import debug_settings, get_active_logger

module_logger = get_active_logger


# NOTE: Calling Singleton classes gives back the already initialized instances only!


def add_catalog(args) -> None:
    catalog = CollectionManager().catalogs().add_by_src(args.src)


def remove_catalog(args) -> None:
    CollectionManager().catalogs().remove_from_collection_by_src(args.src)


# todo: do argument parsing properly
def update(args):
    CollectionManager().catalogs().update_any(getattr(args, "catalog_name", None))


# todo: do argument parsing properly
def upgrade(args):
    dry_run = getattr(args, "dry_run", False)
    updates = CollectionManager().catalogs().update_collection(getattr(args, "catalog_name", None),
                                                               dry_run=dry_run)
    print_json = _get_print_json(args)
    if print_json:
        print(_as_json(updates))
    else:
        if dry_run:
            module_logger().info("An upgrade would apply the following updates:")
        else:
            module_logger().info("Applied the following updates:")
        for change in updates:
            module_logger().info('Catalog: %s' % change.catalog.name)
            if len(change.catalog_attribute_changes) > 0:
                module_logger().info('| Catalog attribute changes')
                for item in change.catalog_attribute_changes:
                    module_logger().info('  name: %s, new value: %s' % (item.attribute, item.new_value))
            if len(change.solution_changes) > 0:
                for item in change.solution_changes:
                    module_logger().info('| %s' % item.coordinates)
                    module_logger().info('  action: %s' % item.change_type)
                    module_logger().info('  changelog: %s' % item.change_log)

            if len(change.catalog_attribute_changes) == 0 and len(change.solution_changes) == 0:
                module_logger().info('| No changes.')


def deploy(args):
    DeployManager().deploy(
        args.path, args.catalog, args.dry_run, args.push_option, args.git_email, args.git_name, args.force_deploy
    )


def install(args):
    InstallManager().install(args.path, sys.argv)


def uninstall(args):
    InstallManager().uninstall(args.path, args.uninstall_deps)


def info(args):
    resolve_result = CollectionManager().resolve_download_and_load(str(args.path))
    print_json = _get_print_json(args)
    deploy_dict = resolve_result.loaded_solution.get_deploy_dict()
    if print_json:
        print(_as_json(deploy_dict))
    else:
        param_example_str = ""
        for arg in deploy_dict["args"]:
            param_example_str += "--%s PARAMETER_VALUE " % arg["name"]
        module_logger().info('')
        module_logger().info('Solution details about %s:' % args.path)
        module_logger().info('|')
        for key in deploy_dict:
            module_logger().info("| %s: %s" % (key, deploy_dict[key]))
        module_logger().info('')
        module_logger().info('Usage:')
        module_logger().info('|')
        module_logger().info('| album install %s', args.path)
        module_logger().info('| album run %s %s' % (resolve_result.loaded_solution.coordinates, param_example_str))
        module_logger().info('| album test %s' % (resolve_result.loaded_solution.coordinates))
        module_logger().info('| album uninstall %s' % (resolve_result.loaded_solution.coordinates))
        module_logger().info('')
        module_logger().info('Run parameters:')
        module_logger().info('|')
        for arg in deploy_dict["args"]:
            module_logger().info('| --%s: %s' % (arg["name"], arg["description"]))


def run(args):
    RunManager().run(args.path, args.run_immediately, sys.argv)


def search(args):
    print_json = _get_print_json(args)
    search_result = SearchManager().search(args.keywords)
    if print_json:
        print(_as_json(search_result))
    else:
        if len(search_result) > 0:
            module_logger().info('Search results for "%s" - run `album info SOLUTION_ID` for more information:' % ' '.join(args.keywords))
            module_logger().info("[SCORE] SOLUTION_ID")
            for result in search_result:
                module_logger().info("[%s] %s" % (result[1], result[0]))
        else:
            module_logger().info('No search results for "%s".' % ' '.join(args.keywords))


def start_server(args):
    server = AlbumServer(args.port, args.host)
    server.setup()
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
        module_logger().info('Catalogs in your local collection:')
        if 'catalogs' in index_dict:
            for catalog in index_dict['catalogs']:
                module_logger().info('Catalog \'%s\':' % catalog['name'])
                module_logger().info('| name: %s' % catalog['name'])
                module_logger().info('| path: %s' % catalog['path'])
                module_logger().info('| catalog_id: %s' % catalog['catalog_id'])
                module_logger().info('| deletable: %s' % catalog['deletable'])
                if len(catalog['solutions']) > 0:
                    module_logger().info('| solutions:')
                    for solution in catalog['solutions']:
                        module_logger().info('| \t%s:%s:%s' % (solution['group'], solution['name'], solution['version']))


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


def _get_print_json(args):
    return getattr(args, "json", False)


def _as_json(data):
    return json.dumps(data, sort_keys=True, indent=4)



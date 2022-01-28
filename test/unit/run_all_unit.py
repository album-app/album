import unittest

from test.unit import test_argument_parsing, test_server
from test.unit.ci import test_ci_argument_parsing, test_ci_commandline
from test.unit.ci.controller import test_release_manager, test_zenodo_manager
from test.unit.ci.utils import test_continuous_integration
from test.unit.core.controller import test_script_manager
from test.unit.core.controller import test_search_manager, test_install_manager, test_run_manager, test_deploy_manager, \
    test_conda_manager, test_test_manager, test_task_manager, test_clone_manager, test_migration_manager, \
    test_environment_manager
from test.unit.core.controller.collection import test_collection_manager, test_catalog_handler, test_solution_handler
from test.unit.core.model import test_catalog, test_configuration, test_environment, \
    test_catalog_index, test_collection_index, test_coordinates, test_task, test_database
from test.unit.core.utils import test_subcommand
from test.unit.core.utils.export import test_changelog, test_docker
from test.unit.core.utils.operations import test_dict_operations
from test.unit.core.utils.operations import test_url_operations, test_file_operations, test_git_operations, \
    test_resolve_operations, test_solution_operations


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    ### unittests

    # album
    suite.addTests(loader.loadTestsFromModule(test_argument_parsing))
    suite.addTests(loader.loadTestsFromModule(test_server))

    # album core.controller.collection
    suite.addTests(loader.loadTestsFromModule(test_collection_manager))
    suite.addTests(loader.loadTestsFromModule(test_catalog_handler))
    suite.addTests(loader.loadTestsFromModule(test_solution_handler))

    # album core.controller
    suite.addTests(loader.loadTestsFromModule(test_clone_manager))
    suite.addTests(loader.loadTestsFromModule(test_conda_manager))
    suite.addTests(loader.loadTestsFromModule(test_deploy_manager))
    suite.addTests(loader.loadTestsFromModule(test_environment_manager))
    suite.addTests(loader.loadTestsFromModule(test_install_manager))
    suite.addTests(loader.loadTestsFromModule(test_migration_manager))
    suite.addTests(loader.loadTestsFromModule(test_run_manager))
    suite.addTests(loader.loadTestsFromModule(test_search_manager))
    suite.addTests(loader.loadTestsFromModule(test_task_manager))
    suite.addTests(loader.loadTestsFromModule(test_test_manager))
    suite.addTests(loader.loadTestsFromModule(test_script_manager))

    # album.core.model
    suite.addTests(loader.loadTestsFromModule(test_catalog))
    suite.addTests(loader.loadTestsFromModule(test_catalog_index))
    suite.addTests(loader.loadTestsFromModule(test_collection_index))
    suite.addTests(loader.loadTestsFromModule(test_configuration))
    suite.addTests(loader.loadTestsFromModule(test_environment))
    suite.addTests(loader.loadTestsFromModule(test_coordinates))
    suite.addTests(loader.loadTestsFromModule(test_task))

    # album.core.concept
    suite.addTests(loader.loadTestsFromModule(test_database))

    # album.core.utils
    suite.addTests(loader.loadTestsFromModule(test_subcommand))

    # album.core.utils.operations
    suite.addTests(loader.loadTestsFromModule(test_file_operations))
    suite.addTests(loader.loadTestsFromModule(test_git_operations))
    suite.addTests(loader.loadTestsFromModule(test_resolve_operations))
    suite.addTests(loader.loadTestsFromModule(test_url_operations))
    suite.addTests(loader.loadTestsFromModule(test_solution_operations))
    suite.addTests(loader.loadTestsFromModule(test_dict_operations))

    # album.core.utils.export
    suite.addTests(loader.loadTestsFromModule(test_docker))
    suite.addTests(loader.loadTestsFromModule(test_changelog))

    # album.ci
    suite.addTests(loader.loadTestsFromModule(test_ci_argument_parsing))
    suite.addTests(loader.loadTestsFromModule(test_ci_commandline))

    # album.ci.controller
    suite.addTests(loader.loadTestsFromModule(test_release_manager))
    suite.addTests(loader.loadTestsFromModule(test_zenodo_manager))

    # album.ci.utils
    suite.addTests(loader.loadTestsFromModule(test_continuous_integration))
    #suite.addTests(loader.loadTestsFromModule(test_zenodo_api))

    runner = unittest.TextTestRunner(verbosity=3)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("Success")
        exit(0)
    else:
        print("Failed")
        exit(1)


main()

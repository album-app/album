import unittest

from test.unit.core import test__init__, test_argument_parsing, test_server
from test.unit.core.concept import test_singleton, test_database
from test.unit.core.contoller import test_search_manager, test_install_manager, test_run_manager, test_deploy_manager, \
    test_conda_manager, test_test_manager, test_task_manager, \
    test_catalog_manager
from test.unit.core.model import test_catalog, test_configuration, test_environment, \
    test_album_base, test_catalog_index, test_collection_index, test_log_handler
from test.unit.core.utils import test_script, test_subcommand
from test.unit.core.utils.operations import test_url_operations, test_file_operations, test_git_operations, \
    test_resolve_operations


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    # ### unittests

    # album.core
    suite.addTests(loader.loadTestsFromModule(test__init__))
    suite.addTests(loader.loadTestsFromModule(test_argument_parsing))
    suite.addTests(loader.loadTestsFromModule(test_server))

    # album core.controller
    suite.addTests(loader.loadTestsFromModule(test_catalog_manager))
    suite.addTests(loader.loadTestsFromModule(test_deploy_manager))
    suite.addTests(loader.loadTestsFromModule(test_install_manager))
    suite.addTests(loader.loadTestsFromModule(test_run_manager))
    suite.addTests(loader.loadTestsFromModule(test_search_manager))
    suite.addTests(loader.loadTestsFromModule(test_conda_manager))
    suite.addTests(loader.loadTestsFromModule(test_test_manager))
    suite.addTests(loader.loadTestsFromModule(test_task_manager))

    # album.core.model
    suite.addTests(loader.loadTestsFromModule(test_catalog))
    suite.addTests(loader.loadTestsFromModule(test_catalog_index))
    suite.addTests(loader.loadTestsFromModule(test_configuration))
    suite.addTests(loader.loadTestsFromModule(test_environment))
    suite.addTests(loader.loadTestsFromModule(test_album_base))
    suite.addTests(loader.loadTestsFromModule(test_collection_index))
    suite.addTests(loader.loadTestsFromModule(test_log_handler))

    # concept
    suite.addTests(loader.loadTestsFromModule(test_singleton))
    suite.addTests(loader.loadTestsFromModule(test_database))

    # album.core.utils
    suite.addTests(loader.loadTestsFromModule(test_script))
    suite.addTests(loader.loadTestsFromModule(test_subcommand))

    # album.core.utils.operations
    suite.addTests(loader.loadTestsFromModule(test_file_operations))
    suite.addTests(loader.loadTestsFromModule(test_git_operations))
    suite.addTests(loader.loadTestsFromModule(test_url_operations))
    suite.addTests(loader.loadTestsFromModule(test_resolve_operations))

    runner = unittest.TextTestRunner(verbosity=3)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("Success")
        exit(0)
    else:
        print("Failed")
        exit(1)


main()

import unittest

from test.unit.ci.utils import test_ci_utils
from test.unit.core import test__init__, test_argument_parsing
from test.unit.core.contoller import test_search_manager, test_install_manager, test_run_manager, test_deploy_manager, \
    test_catalog_manager, test_conda_manager
from test.unit.core.model import test_catalog, test_configuration, test_catalog_configuration, test_environment, \
    test_hips_base
from test.unit.core.concept import test_singleton
from test.unit.core.utils import test_script, test_subcommand
from test.unit.core.utils.operations import test_url_operations, test_file_operations, test_git_operations


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    # ### unittests

    # hips.core
    suite.addTests(loader.loadTestsFromModule(test__init__))
    suite.addTests(loader.loadTestsFromModule(test_argument_parsing))

    # hips core.controller
    suite.addTests(loader.loadTestsFromModule(test_deploy_manager))
    suite.addTests(loader.loadTestsFromModule(test_install_manager))
    suite.addTests(loader.loadTestsFromModule(test_run_manager))
    suite.addTests(loader.loadTestsFromModule(test_search_manager))
    suite.addTests(loader.loadTestsFromModule(test_catalog_manager))
    suite.addTests(loader.loadTestsFromModule(test_conda_manager))

    # hips.core.model
    suite.addTests(loader.loadTestsFromModule(test_catalog))
    suite.addTests(loader.loadTestsFromModule(test_configuration))
    suite.addTests(loader.loadTestsFromModule(test_catalog_configuration))
    suite.addTests(loader.loadTestsFromModule(test_environment))
    suite.addTests(loader.loadTestsFromModule(test_hips_base))

    # concept
    suite.addTests(loader.loadTestsFromModule(test_singleton))

    # hips.core.utils
    suite.addTests(loader.loadTestsFromModule(test_script))
    suite.addTests(loader.loadTestsFromModule(test_subcommand))

    # hips.core.utils.operations
    suite.addTests(loader.loadTestsFromModule(test_file_operations))
    suite.addTests(loader.loadTestsFromModule(test_git_operations))
    suite.addTests(loader.loadTestsFromModule(test_url_operations))

    # extensions

    # hips.ci
    suite.addTests(loader.loadTestsFromModule(test_ci_utils))
    # suite.addTests(loader.loadTestsFromModule(test_zenodo_api))

    runner = unittest.TextTestRunner(verbosity=3)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("Success")
        exit(0)
    else:
        print("Failed")
        exit(1)


main()

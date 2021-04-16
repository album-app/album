import unittest

from test.integration import test_integration_cmdline
from test.unit.hips import test_run, test_install, test__init__, test_cmdline, test_deploy, test_api, test_search
from test.unit.hips_utils import test_hips_logging, test_zenodo_api, test_environment,\
    test_hips_catalog, test_hips_configuration
from test.unit.hips_utils.operations import test_file_operations, test_git_operations, test_url_operations


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    # ### unittests
    # hips
    suite.addTests(loader.loadTestsFromModule(test__init__))
    suite.addTests(loader.loadTestsFromModule(test_api))
    suite.addTests(loader.loadTestsFromModule(test_cmdline))
    suite.addTests(loader.loadTestsFromModule(test_deploy))
    suite.addTests(loader.loadTestsFromModule(test_install))
    suite.addTests(loader.loadTestsFromModule(test_run))
    suite.addTests(loader.loadTestsFromModule(test_search))

    # hips utils operations
    suite.addTests(loader.loadTestsFromModule(test_file_operations))
    suite.addTests(loader.loadTestsFromModule(test_git_operations))
    suite.addTests(loader.loadTestsFromModule(test_url_operations))

    # hips_utils
    suite.addTests(loader.loadTestsFromModule(test_environment))
    suite.addTests(loader.loadTestsFromModule(test_hips_catalog))
    suite.addTests(loader.loadTestsFromModule(test_hips_configuration))
    suite.addTests(loader.loadTestsFromModule(test_hips_logging))
    suite.addTests(loader.loadTestsFromModule(test_zenodo_api))

    # ### integration
    suite.addTests(loader.loadTestsFromModule(test_integration_cmdline))

    runner = unittest.TextTestRunner(verbosity=3)
    result = runner.run(suite)
    if result.wasSuccessful():
        exit(0)
    else:
        exit(1)


main()

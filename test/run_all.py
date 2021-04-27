import unittest

from test.integration import test_integration_cmdline
from test.unit.hips.api import test_install_helper
from test.unit.hips.api import test_run_helper
from test.unit.hips.ci import test_zenodo_api
from test.unit.hips.core import test_search, test__init__, test_install, test_run, test_deploy, test_cmdline
from test.unit.hips.core.utils import test_script
from test.unit.hips.core.model import test_catalog, test_environment, test_logging, test_configuration, test_resolve
from test.unit.hips.core.utils.operations import test_url_operations, test_file_operations, test_git_operations


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    # ### unittests
    # hips.api
    suite.addTests(loader.loadTestsFromModule(test_install_helper))
    suite.addTests(loader.loadTestsFromModule(test_run_helper))

    # hips.core
    suite.addTests(loader.loadTestsFromModule(test__init__))
    suite.addTests(loader.loadTestsFromModule(test_cmdline))
    suite.addTests(loader.loadTestsFromModule(test_deploy))
    suite.addTests(loader.loadTestsFromModule(test_install))
    suite.addTests(loader.loadTestsFromModule(test_run))
    suite.addTests(loader.loadTestsFromModule(test_search))

    # hips.core.model
    suite.addTests(loader.loadTestsFromModule(test_catalog))
    suite.addTests(loader.loadTestsFromModule(test_configuration))
    suite.addTests(loader.loadTestsFromModule(test_environment))
    suite.addTests(loader.loadTestsFromModule(test_logging))
    suite.addTests(loader.loadTestsFromModule(test_resolve))

    # hips.core.utils
    suite.addTests(loader.loadTestsFromModule(test_script))

    # hips.core.utils.operations
    suite.addTests(loader.loadTestsFromModule(test_file_operations))
    suite.addTests(loader.loadTestsFromModule(test_git_operations))
    suite.addTests(loader.loadTestsFromModule(test_url_operations))

    # extensions

    # hips.ci

    # hips.ci.utils
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

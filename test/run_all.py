import unittest

from test.unit.hips import test_run, test_install, test__init__, test_cmdline
from test.unit.install_helper import test_modules
from test.integration import test_integration_cmdline
from test.unit.utils import test_hips_logging, test_zenodo_api, test_environment


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(test__init__))
    suite.addTests(loader.loadTestsFromModule(test_cmdline))
    suite.addTests(loader.loadTestsFromModule(test_integration_cmdline))
    suite.addTests(loader.loadTestsFromModule(test_hips_logging))
    suite.addTests(loader.loadTestsFromModule(test_zenodo_api))
    suite.addTests(loader.loadTestsFromModule(test_run))
    suite.addTests(loader.loadTestsFromModule(test_install))
    suite.addTests(loader.loadTestsFromModule(test_modules))
    suite.addTests(loader.loadTestsFromModule(test_environment))
    runner = unittest.TextTestRunner(verbosity=3)
    result = runner.run(suite)
    if result.wasSuccessful():
        exit(0)
    else:
        exit(1)


main()

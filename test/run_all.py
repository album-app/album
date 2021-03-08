import unittest

from test.hips import test__init__
from test.hips import test_cmdline
from test.hips import test_run
from test.hips import test_install
from test.install_helper import test_modules
from test.integration import test_integration_cmdline
from test.utils import test_hips_logging
from test.utils import test_zenodo_api


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(test_cmdline))
    suite.addTests(loader.loadTestsFromModule(test_integration_cmdline))
    suite.addTests(loader.loadTestsFromModule(test_hips_logging))
    suite.addTests(loader.loadTestsFromModule(test_zenodo_api))
    suite.addTests(loader.loadTestsFromModule(test_run))
    suite.addTests(loader.loadTestsFromModule(test_install))
    suite.addTests(loader.loadTestsFromModule(test__init__))
    suite.addTests(loader.loadTestsFromModule(test_modules))
    runner = unittest.TextTestRunner(verbosity=3)
    result = runner.run(suite)
    if result.wasSuccessful():
        exit(0)
    else:
        exit(1)


main()

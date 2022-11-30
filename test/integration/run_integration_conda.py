import time
import unittest

from test.integration.core import test_integration_filestructure
from test.integration.core import (
    test_integration_run,
    test_integration_test,
    test_integration_install,
    test_integration_catalog_features,
)


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    ### integration

    # Core
    suite.addTests(loader.loadTestsFromModule(test_integration_install))
    suite.addTests(loader.loadTestsFromModule(test_integration_run))
    suite.addTests(loader.loadTestsFromModule(test_integration_test))

    runner = unittest.TextTestRunner(verbosity=3)
    result = runner.run(suite)
    if result.wasSuccessful():
        time.sleep(5)
        print("Success")
        exit(0)
    else:
        print("Failed")
        exit(1)


main()

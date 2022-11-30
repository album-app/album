import time
import unittest

from test.unit.core.controller import (
    test_conda_manager,
    test_environment_manager,
)
from test.unit.core.controller import test_mamba_manager


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    ### unittests

    # album core.controller
    suite.addTests(loader.loadTestsFromModule(test_mamba_manager))
    suite.addTests(loader.loadTestsFromModule(test_environment_manager))

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

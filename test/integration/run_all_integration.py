import unittest

from test.integration.ci import test_integration_ci
from test.integration.core import test_integration_uninstall, test_integration_server, test_integration_run, \
    test_integration_search, test_integration_test, test_integration_repl, \
    test_integration_install, test_integration_catalog_features, test_integration_deploy, test_integration_clone


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # ### integration
    suite.addTests(loader.loadTestsFromModule(test_integration_catalog_features))
    suite.addTests(loader.loadTestsFromModule(test_integration_deploy))
    suite.addTests(loader.loadTestsFromModule(test_integration_install))
    suite.addTests(loader.loadTestsFromModule(test_integration_uninstall))
    suite.addTests(loader.loadTestsFromModule(test_integration_repl))
    suite.addTests(loader.loadTestsFromModule(test_integration_run))
    suite.addTests(loader.loadTestsFromModule(test_integration_search))
    suite.addTests(loader.loadTestsFromModule(test_integration_test))
    suite.addTests(loader.loadTestsFromModule(test_integration_clone))
    suite.addTests(loader.loadTestsFromModule(test_integration_server))

    # CI
    suite.addTests(loader.loadTestsFromModule(test_integration_ci))

    runner = unittest.TextTestRunner(verbosity=3)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("Success")
        exit(0)
    else:
        print("Failed")
        exit(1)


main()

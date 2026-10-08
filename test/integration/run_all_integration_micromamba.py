"""Run all integration tests as one suite.

Importing this module runs nothing. Entry points:

* ``python -m test.integration.run_all_integration_micromamba`` runs ``main()``
  (verbose runner, prints Success/Failed, exits 0/1); used by CI.
* ``python -m unittest test/integration/run_all_integration_micromamba.py`` collects
  the same suite through ``load_tests``.
"""

import sys
import time
import unittest
from test.integration import (
    test_integration_api,
    test_integration_commandline,
    test_integration_resource_api_version,
)
from test.integration.ci import test_integration_ci
from test.integration.core import (
    test_integration_backwards_compatibility,
    test_integration_catalog_features,
    test_integration_clone,
    test_integration_deploy,
    test_integration_environment_preparation,
    test_integration_filestructure,
    test_integration_install,
    test_integration_migration_manager,
    test_integration_repl,
    test_integration_run,
    test_integration_search,
    test_integration_test,
    test_integration_uninstall,
)


def load_tests(loader, standard_tests, pattern):
    """Return the aggregated suite (unittest ``load_tests`` protocol)."""
    suite = unittest.TestSuite()

    ### integration

    # album
    suite.addTests(loader.loadTestsFromModule(test_integration_api))
    suite.addTests(loader.loadTestsFromModule(test_integration_commandline))
    suite.addTests(loader.loadTestsFromModule(test_integration_resource_api_version))

    # Core
    suite.addTests(loader.loadTestsFromModule(test_integration_backwards_compatibility))
    suite.addTests(loader.loadTestsFromModule(test_integration_catalog_features))
    suite.addTests(loader.loadTestsFromModule(test_integration_clone))
    suite.addTests(loader.loadTestsFromModule(test_integration_deploy))
    suite.addTests(loader.loadTestsFromModule(test_integration_environment_preparation))
    suite.addTests(loader.loadTestsFromModule(test_integration_filestructure))
    suite.addTests(loader.loadTestsFromModule(test_integration_install))
    suite.addTests(loader.loadTestsFromModule(test_integration_migration_manager))
    suite.addTests(loader.loadTestsFromModule(test_integration_repl))
    suite.addTests(loader.loadTestsFromModule(test_integration_run))
    suite.addTests(loader.loadTestsFromModule(test_integration_search))
    # suite.addTests(loader.loadTestsFromModule(test_integration_task_manager)) # todo: fix me
    suite.addTests(loader.loadTestsFromModule(test_integration_test))
    suite.addTests(loader.loadTestsFromModule(test_integration_uninstall))

    # CI
    suite.addTests(loader.loadTestsFromModule(test_integration_ci))

    return suite


def main():
    suite = load_tests(unittest.TestLoader(), None, None)
    runner = unittest.TextTestRunner(verbosity=3)
    result = runner.run(suite)
    if result.wasSuccessful():
        time.sleep(5)
        print("Success")
        sys.exit(0)
    else:
        print("Failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

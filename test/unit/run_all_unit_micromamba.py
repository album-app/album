"""Run all unit tests as one suite.

Importing this module runs nothing. Entry points:

* ``python -m test.unit.run_all_unit_micromamba`` runs ``main()``
  (verbose runner, prints Success/Failed, exits 0/1); used by CI.
* ``python -m unittest test/unit/run_all_unit_micromamba.py`` collects
  the same suite through ``load_tests``.
"""

import sys
import time
import unittest
from test.unit import test_argument_parsing
from test.unit.ci import test_ci_argument_parsing, test_ci_commandline
from test.unit.ci.controller import test_release_manager, test_zenodo_manager
from test.unit.ci.utils import test_continuous_integration
from test.unit.core import test_core_metadata
from test.unit.core.controller import (
    test_clone_manager,
    test_deploy_manager,
    test_environment_manager,
    test_event_manager,
    test_install_manager,
    test_migration_manager,
    test_resource_manager,
    test_run_manager,
    test_script_manager,
    test_search_manager,
    test_shared_downloads_manager,
    test_state_manager,
    test_task_manager,
    test_test_manager,
)
from test.unit.core.controller.collection import (
    test_catalog_handler,
    test_collection_manager,
    test_solution_handler,
)
from test.unit.core.model import (
    test_catalog,
    test_catalog_index,
    test_collection_index,
    test_configuration,
    test_database,
    test_mmversion,
    test_task,
)
from test.unit.core.utils.export import test_changelog, test_docker
from test.unit.core.utils.operations import (
    test_dict_operations,
    test_file_operations,
    test_git_operations,
    test_resolve_operations,
    test_solution_operations,
    test_url_operations,
    test_view_operations,
)
from test.unit.core.utils.runner import test_backwards_compatibility_0_6_1


def load_tests(loader, standard_tests, pattern):
    """Return the aggregated suite (unittest ``load_tests`` protocol)."""
    suite = unittest.TestSuite()
    ### unittests

    # album
    suite.addTests(loader.loadTestsFromModule(test_argument_parsing))

    # album core
    suite.addTests(loader.loadTestsFromModule(test_core_metadata))

    # album core.controller.collection
    suite.addTests(loader.loadTestsFromModule(test_collection_manager))
    suite.addTests(loader.loadTestsFromModule(test_catalog_handler))
    suite.addTests(loader.loadTestsFromModule(test_solution_handler))

    # album core.controller
    suite.addTests(loader.loadTestsFromModule(test_clone_manager))
    suite.addTests(loader.loadTestsFromModule(test_deploy_manager))
    suite.addTests(loader.loadTestsFromModule(test_environment_manager))
    suite.addTests(loader.loadTestsFromModule(test_install_manager))
    suite.addTests(loader.loadTestsFromModule(test_migration_manager))
    suite.addTests(loader.loadTestsFromModule(test_resource_manager))
    suite.addTests(loader.loadTestsFromModule(test_run_manager))
    suite.addTests(loader.loadTestsFromModule(test_search_manager))
    suite.addTests(loader.loadTestsFromModule(test_task_manager))
    suite.addTests(loader.loadTestsFromModule(test_test_manager))
    suite.addTests(loader.loadTestsFromModule(test_script_manager))
    suite.addTests(loader.loadTestsFromModule(test_event_manager))
    suite.addTests(loader.loadTestsFromModule(test_state_manager))
    suite.addTests(loader.loadTestsFromModule(test_shared_downloads_manager))

    # album.core.model
    suite.addTests(loader.loadTestsFromModule(test_catalog))
    suite.addTests(loader.loadTestsFromModule(test_catalog_index))
    suite.addTests(loader.loadTestsFromModule(test_collection_index))
    suite.addTests(loader.loadTestsFromModule(test_configuration))
    suite.addTests(loader.loadTestsFromModule(test_task))
    suite.addTests(loader.loadTestsFromModule(test_mmversion))

    # album.core.concept
    suite.addTests(loader.loadTestsFromModule(test_database))

    # album.core.utils.operations
    suite.addTests(loader.loadTestsFromModule(test_file_operations))
    suite.addTests(loader.loadTestsFromModule(test_git_operations))
    suite.addTests(loader.loadTestsFromModule(test_resolve_operations))
    suite.addTests(loader.loadTestsFromModule(test_url_operations))
    suite.addTests(loader.loadTestsFromModule(test_solution_operations))
    suite.addTests(loader.loadTestsFromModule(test_dict_operations))
    suite.addTests(loader.loadTestsFromModule(test_view_operations))

    # album.core.utils.export
    suite.addTests(loader.loadTestsFromModule(test_docker))
    suite.addTests(loader.loadTestsFromModule(test_changelog))

    # album.core.utils.runner (the frozen <= 0.6.1 solution runner)
    suite.addTests(loader.loadTestsFromModule(test_backwards_compatibility_0_6_1))

    # album.ci
    suite.addTests(loader.loadTestsFromModule(test_ci_argument_parsing))
    suite.addTests(loader.loadTestsFromModule(test_ci_commandline))

    # album.ci.controller
    suite.addTests(loader.loadTestsFromModule(test_release_manager))
    suite.addTests(loader.loadTestsFromModule(test_zenodo_manager))

    # album.ci.utils
    suite.addTests(loader.loadTestsFromModule(test_continuous_integration))
    # suite.addTests(loader.loadTestsFromModule(test_zenodo_api))

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

from queue import Queue

from album.core.controller.conda_manager import CondaManager

from album.core.concept.singleton import Singleton
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.controller.run_manager import RunManager
from album.runner import logging
from album.core.model.coordinates import Coordinates

module_logger = logging.get_active_logger


class TestManager(metaclass=Singleton):
    """Class managing testing routine of a solution. Similar to the installation process, a configured \"test \"
    routine of a solution is executed in the target environment (The conda environment the solution lives in).
    Solutions must be installed to run their testing routine.

     Attributes:
         collection_manager:
            Holding all configured catalogs. Resolves inside our outside catalogs.

    """
    # singletons
    collection_manager = None
    conda_manager = None
    run_manager = None

    def __init__(self):
        self.collection_manager = CollectionManager()
        self.conda_manager = CondaManager()
        self.run_manager = RunManager()

    def test(self, path, args=None):
        """Function corresponding to the `test` subcommand of `album`."""
        if args is None:
            args = [""]
        try:
            resolve_result = self.collection_manager.resolve_require_installation_and_load(path)
        except ValueError:
            raise ValueError("Solution points to a local file which has not been installed yet. "
                             "Please point to an installation from the catalog or install the solution. "
                             "Aborting...")

        if not resolve_result.loaded_solution.parent:
            resolve_result.loaded_solution.set_environment(resolve_result.catalog.name)

        if not resolve_result.catalog:
            module_logger().debug('album loaded locally: %s...' % str(resolve_result.loaded_solution))
        else:
            module_logger().debug('album loaded from catalog: %s...' % str(resolve_result.loaded_solution))

        self._test(resolve_result.loaded_solution, args)

        module_logger().info('Test run for %s!' % resolve_result.loaded_solution['name'])

    def test_from_catalog_coordinates(self, catalog_name: str, coordinates: Coordinates, argv=None):
        catalog = self.collection_manager.catalogs().get_by_name(catalog_name)
        resolve_result = self.collection_manager.resolve_download_and_load_catalog_coordinates(catalog, coordinates)
        self._test(resolve_result.loaded_solution, argv)

    def test_from_coordinates(self, coordinates: Coordinates, argv=None):
        resolve_result = self.collection_manager.resolve_download_and_load_coordinates(coordinates)
        self._test(resolve_result.loaded_solution, argv)

    def _test(self, active_solution, args=None):
        if args is None:
            args = [""]
        if active_solution['pre_test'] and callable(active_solution['pre_test']) \
                and active_solution['test'] and callable(active_solution['test']):
            module_logger().debug('Creating test script...')

            # set init of run_manager to include pre_test call and argument parsing before run
            self.run_manager.init_script = "\nd = get_active_solution().pre_test()\n"
            self.run_manager.init_script += "\nsys.argv = sys.argv + [\"=\".join([c, d[c]]) for c in d]\n"

            # parse args again after pre_test() routine if necessary.
            if not active_solution["args"] == "pass-through":
                self.run_manager.init_script += "\nget_active_solution().args = parser.parse_args()\n"

            # prepare run_script
            que = Queue()
            self.run_manager.build_queue(active_solution, que, False, args)  # do not run queue immediately
            _, scripts = que.get(block=False)

            # add test_routine to script
            if len(scripts) > 1:
                scripts.append("\nget_active_solution().test()\n")
            else:
                scripts[0] += "\nget_active_solution().test()\n"

            module_logger().debug('Calling test routine specified in solution...')
            logging.configure_logging(active_solution['name'])
            self.conda_manager.set_environment_path(active_solution.environment)
            self.conda_manager.run_scripts(active_solution.environment, scripts)
            logging.pop_active_logger()
        else:
            module_logger().warning('No \"test\" routine configured for solution %s! Skipping...' % active_solution['name'])

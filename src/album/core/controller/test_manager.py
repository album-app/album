from queue import Queue

from album.core.concept.singleton import Singleton
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.controller.conda_manager import CondaManager
from album.core.controller.environment_manager import EnvironmentManager
from album.core.controller.run_manager import RunManager
from album.core.model.coordinates import Coordinates
from album.core.utils.script import ScriptTestCreator
from album.runner import album_logging

module_logger = album_logging.get_active_logger


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
    environment_manager = None

    def __init__(self):
        self.collection_manager = CollectionManager()
        self.conda_manager = CondaManager()
        self.run_manager = RunManager()
        self.environment_manager = EnvironmentManager()

    def test(self, path, args=None):
        """Function corresponding to the `test` subcommand of `album`."""
        if args is None:
            args = [""]

        # resolve the input
        resolve_result = self.collection_manager.resolve_require_installation_and_load(path)

        # set the environment
        self.environment_manager.set_environment(resolve_result.loaded_solution, resolve_result.catalog)

        self._test(resolve_result.loaded_solution, args)

        module_logger().info('Ran test routine for %s!' % resolve_result.loaded_solution['name'])

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

            # prepare run_script
            que = Queue()
            script_test_creator = ScriptTestCreator()
            self.run_manager.build_queue(active_solution, que, script_test_creator, False, args)  # do not run queue immediately
            _, scripts = que.get(block=False)

            module_logger().debug('Calling test routine specified in solution...')
            album_logging.configure_logging(active_solution['name'])

            self.conda_manager.run_scripts(active_solution.environment, scripts)
            album_logging.pop_active_logger()
        else:
            module_logger().warning(
                'No \"test\" routine configured for solution %s! Skipping...' % active_solution['name']
            )

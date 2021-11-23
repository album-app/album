from queue import Queue

from album.core.concept.singleton import Singleton
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.controller.environment_manager import EnvironmentManager
from album.core.controller.run_manager import RunManager
from album.core.model.resolve_result import ResolveResult
from album.runner import album_logging
from album.runner.concept.script_creator import ScriptTestCreator
from album.runner.model.coordinates import Coordinates

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
    run_manager = None
    environment_manager = None

    def __init__(self):
        self.collection_manager = CollectionManager()
        self.run_manager = RunManager()
        self.environment_manager = EnvironmentManager()

    def test(self, path, args=None):
        """Function corresponding to the `test` subcommand of `album`."""
        if args is None:
            args = [""]

        # resolve the input
        resolve_result = self.collection_manager.resolve_require_installation_and_load(path)

        self._test(resolve_result, args)

        module_logger().info('Ran test routine for \"%s\"!' % resolve_result.loaded_solution.coordinates.name)

    def test_from_catalog_coordinates(self, catalog_name: str, coordinates: Coordinates, argv=None):
        catalog = self.collection_manager.catalogs().get_by_name(catalog_name)
        resolve_result = self.collection_manager.resolve_download_and_load_catalog_coordinates(catalog, coordinates)

        self._test(resolve_result, argv)

    def test_from_coordinates(self, coordinates: Coordinates, argv=None):
        resolve_result = self.collection_manager.resolve_download_and_load_coordinates(coordinates)
        self._test(resolve_result, argv)

    def _test(self, resolve_result: ResolveResult, args=None):
        if args is None:
            args = [""]

        solution = resolve_result.loaded_solution

        if resolve_result.loaded_solution.setup.pre_test and callable(solution.setup.pre_test) \
                and solution.setup.test and callable(solution.setup.test):
            queue = Queue()
            script_test_creator = ScriptTestCreator()

            # do not run queue immediately
            self.run_manager.build_queue(resolve_result.loaded_solution, resolve_result.catalog, queue, script_test_creator, False, args)

            # runs the queue
            self.run_manager.run_queue(queue)
        else:
            module_logger().warning(
                'No \"test\" routine configured for solution \"%s\"! Skipping...' % solution.coordinates.name
            )

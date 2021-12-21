from queue import Queue

from album.core.api.album import IAlbum
from album.core.api.controller.test_manager import ITestManager
from album.core.api.model.resolve_result import IResolveResult
from album.runner import album_logging
from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.model.script_creator import ScriptCreatorTest

module_logger = album_logging.get_active_logger


class TestManager(ITestManager):

    def __init__(self, album: IAlbum):
        self.album = album

    def test(self, path, args=None):
        if args is None:
            args = [""]

        # resolve the input
        resolve_result = self.album.collection_manager().resolve_require_installation_and_load(path)

        self._test(resolve_result, args)

        module_logger().info('Ran test routine for \"%s\"!' % resolve_result.loaded_solution().coordinates().name())

    def test_from_catalog_coordinates(self, catalog_name: str, coordinates: ICoordinates, argv=None):
        catalog = self.album.collection_manager().catalogs().get_by_name(catalog_name)
        resolve_result = self.album.collection_manager().resolve_download_and_load_catalog_coordinates(
            catalog,
            coordinates
        )

        self._test(resolve_result, argv)

    def test_from_coordinates(self, coordinates: ICoordinates, argv=None):
        resolve_result = self.album.collection_manager().resolve_download_and_load_coordinates(coordinates)
        self._test(resolve_result, argv)

    def _test(self, resolve_result: IResolveResult, args=None):
        if args is None:
            args = [""]

        solution = resolve_result.loaded_solution()

        if solution.setup().pre_test and callable(solution.setup().pre_test) \
                and solution.setup().test and callable(solution.setup().test):
            queue = Queue()
            script_test_creator = ScriptCreatorTest()

            # do not run queue immediately
            self.album.run_manager().build_queue(
                solution, resolve_result.catalog(), queue, script_test_creator, False, args
            )

            # runs the queue
            self.album.run_manager().run_queue(queue)
        else:
            module_logger().warning(
                'No \"test\" routine configured for solution \"%s\"! Skipping...' % solution.coordinates().name()
            )

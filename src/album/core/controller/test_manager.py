from queue import Queue
from typing import List, Optional

from album.runner import album_logging
from album.runner.core.api.model.solution import ISolution

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.test_manager import ITestManager

module_logger = album_logging.get_active_logger


class TestManager(ITestManager):
    def __init__(self, album: IAlbumController):
        self.album = album

    def test(self, solution_to_resolve: str, args: Optional[List[str]] = None):
        if args is None:
            args = [""]

        resolve_result = self.album.collection_manager().resolve_installed_and_load(
            solution_to_resolve
        )
        solution = resolve_result.loaded_solution()
        test_routine = solution.setup().test
        pre_test_routine = solution.setup().pre_test

        # "test" is required
        if not callable(test_routine):
            module_logger().warning(
                'No "test" routine configured for solution "%s"! Skipping...'
                % solution.coordinates().name()
            )
            return

        # "pre_test" is optional, but the runner calls it whenever it is set
        if pre_test_routine and not callable(pre_test_routine):
            module_logger().warning(
                'The "pre_test" routine of solution "%s" is not callable! Skipping...'
                % solution.coordinates().name()
            )
            return

        queue: Queue = Queue()

        # do not run queue immediately
        self.album.script_manager().build_queue(
            resolve_result, queue, ISolution.Action.TEST, False, args
        )

        # runs the queue
        self.album.script_manager().run_queue(queue)

        module_logger().info(
            'Ran test routine for "%s"!' % solution.coordinates().name()
        )

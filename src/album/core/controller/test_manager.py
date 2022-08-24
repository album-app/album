from queue import Queue

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.test_manager import ITestManager
from album.runner import album_logging
from album.runner.core.model.script_creator import ScriptCreatorTest

module_logger = album_logging.get_active_logger


class TestManager(ITestManager):
    def __init__(self, album: IAlbumController):
        self.album = album

    def test(self, solution_to_resolve: str, args=None):
        if args is None:
            args = [""]

        resolve_result = self.album.collection_manager().resolve_installed_and_load(
            solution_to_resolve
        )
        solution = resolve_result.loaded_solution()

        if (
            solution.setup().pre_test
            and callable(solution.setup().pre_test)
            and solution.setup().test
            and callable(solution.setup().test)
        ) or (
            not solution.setup().pre_test
            and solution.setup().test
            and callable(solution.setup().test)
        ):
            queue = Queue()
            script_test_creator = ScriptCreatorTest()

            # do not run queue immediately
            self.album.script_manager().build_queue(
                resolve_result, queue, script_test_creator, False, args
            )

            # runs the queue
            self.album.script_manager().run_queue(queue)

            module_logger().info(
                'Ran test routine for "%s"!'
                % resolve_result.loaded_solution().coordinates().name()
            )
        else:
            module_logger().warning(
                'No "test" routine configured for solution "%s"! Skipping...'
                % solution.coordinates().name()
            )

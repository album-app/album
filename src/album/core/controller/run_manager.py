from queue import Queue
from typing import List

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.run_manager import IRunManager
from album.core.api.model.collection_solution import ICollectionSolution
from album.runner import album_logging
from album.runner.core.api.model.solution import ISolution
from album.runner.core.model.script_creator import ScriptCreatorRun

module_logger = album_logging.get_active_logger


class SolutionGroup:

    def __init__(
            self,
            parent_parsed_args=None,
            parent: ICollectionSolution = None,
            steps_solution=None,
            steps=None
    ):
        if parent_parsed_args is None:
            parent_parsed_args = [None]
        if steps_solution is None:
            steps_solution = []
        if steps is None:
            steps = []
        self.parent_parsed_args = parent_parsed_args
        self.parent = parent
        self.steps_solution: List[ISolution] = steps_solution  # The solution objects of all steps.

        self.steps = steps  # The step description of the step. Must hold the argument keyword.

    def __eq__(self, o: object) -> bool:
        return isinstance(o, SolutionGroup) and \
               o.parent.coordinates() == self.parent.coordinates() and \
               o.steps_solution == self.steps_solution and \
               o.steps == self.steps


class RunManager(IRunManager):

    def __init__(self, album: IAlbumController):
        self.album = album

        self.init_script = ""

    def run(self, solution_to_resolve: str, run_immediately=False, argv=None):
        """Run an already loaded solution."""
        resolve_result = self.album.collection_manager().resolve_installed_and_load(solution_to_resolve)
        if not resolve_result.catalog:
            module_logger().debug('solution loaded locally: %s...' % str(resolve_result.loaded_solution().coordinates()))
        else:
            module_logger().debug('solution loaded from catalog: \"%s\"...' % str(resolve_result.loaded_solution().coordinates()))
        module_logger().debug(
            "Initializing script to run \"%s\"" % resolve_result.loaded_solution().coordinates())

        if argv is None:
            argv = [""]

        # pushing album and their scripts to a queue
        que = Queue()

        # builds the queue
        self.album.script_manager().build_queue(resolve_result, que, ScriptCreatorRun(), run_immediately, argv)

        # runs the queue
        self.album.script_manager().run_queue(que)

        module_logger().debug(
            "Finished running script for solution \"%s\"" % resolve_result.loaded_solution().coordinates().name())

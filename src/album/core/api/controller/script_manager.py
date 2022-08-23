from abc import ABCMeta, abstractmethod
from queue import Queue

from album.core.api.model.collection_solution import ICollectionSolution
from album.runner.core.api.model.script_creator import IScriptCreator


class IScriptManager:
    __metaclass__ = ABCMeta

    @abstractmethod
    def run_queue(self, queue: Queue):
        """Runs the que. Queue consists of "solution_object and their scripts"-entries. Order matters!

        Args:
            queue:
                The queue object holding entries of solution_object and their scripts

        """
        raise NotImplementedError

    @abstractmethod
    def build_queue(
        self,
        solution: ICollectionSolution,
        queue,
        script_creator: IScriptCreator,
        run_immediately=False,
        argv=None,
    ):
        """Builds the queue of an active-album object.

        Args:
            script_creator:
                The ScriptCreatorRun object to use to create the execution script.
            solution:
                The resolve_result of a solution object to build the run-que for.
            queue:
                The que object.
            run_immediately:
                Boolean. When true, a collection is run immediately without solving for further steps and pushing them
                to the queue. Can result in resolving problems in further downstream collections. Necessary for
                branching decisions.
            argv:
                The argument vector being passed to the solution.

        """
        raise NotImplementedError

    @abstractmethod
    def run_solution_script(
        self, resolve_result: ICollectionSolution, script: IScriptCreator
    ):
        raise NotImplementedError

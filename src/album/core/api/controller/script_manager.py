"""Interface for the script manager."""
from abc import ABCMeta, abstractmethod
from queue import Queue
from typing import List, Optional

from album.runner.core.api.model.solution import ISolution

from album.core.api.model.collection_solution import ICollectionSolution


class IScriptManager:
    """Interface for the script manager."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def run_queue(self, queue: Queue, pipe_output: bool = True) -> None:
        """Run the que.

        Queue consists of "solution_object and their scripts"-entries. Order matters!

        Args:
            queue:
                The queue object holding entries of solution_object and their scripts

        """
        raise NotImplementedError

    @abstractmethod
    def build_queue(
        self,
        collection_solution: ICollectionSolution,
        queue: Queue,
        solution_action: ISolution.Action,
        run_immediately: bool = False,
        argv: Optional[List[str]] = None,
    ) -> None:
        """Build the queue of an active-album object.

        Args:
            solution_action:
                The action to trigger when executing the solution (i.e. run, install, or test).
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
        self,
        resolve_result: ICollectionSolution,
        solution_action: ISolution.Action,
        pipe_output: bool = True,
    ) -> None:
        """Run the solution script."""
        raise NotImplementedError

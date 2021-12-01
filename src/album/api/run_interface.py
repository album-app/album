from abc import ABCMeta, abstractmethod
from queue import Queue

from album.core.model.catalog import Catalog
from album.runner.model.solution import Solution
from album.runner.concept.script_creator import ScriptCreatorRun
from album.runner.model.coordinates import Coordinates


class RunInterface:
    """Interface managing the running process of a solution.

    A solution is executed in its target environment which is created during installation. This class performs all
    operations necessary to run a solution. Resolving of a solution in all configured catalogs,
    dependency checking, and more.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def run(self, path, run_immediately=False, argv=None):
        """Function corresponding to the `run` subcommand of `album`."""
        raise NotImplementedError

    @abstractmethod
    def run_from_catalog_coordinates(self, catalog_name: str, coordinates: Coordinates, run_immediately=False,
                                         argv=None):
        raise NotImplementedError

    @abstractmethod
    def run_from_coordinates(self, coordinates: Coordinates, run_immediately=False, argv=None):
        raise NotImplementedError

    @abstractmethod
    def run_queue(self, queue: Queue):
        """Runs the que. Queue consists of "solution_object and their scripts"-entries. Order matters!

        Args:
            queue:
                The queue object holding entries of solution_object and their scripts

        """
        raise NotImplementedError

    @abstractmethod
    def build_queue(self, solution: Solution, catalog: Catalog, queue, script_creator: ScriptCreatorRun, run_immediately=False,
                    argv=None):
        """Builds the queue of an active-album object.

        Args:
            script_creator:
                The ScriptCreatorRun object to use to create the execution script.
            solution:
                The resolve_result of a solution object to build the run-que for.
            catalog:
                The catalog this solution belongs to.
            queue:
                The que object.
            run_immediately:
                Boolean. When true, a collection is run immediately without solving for further steps and pushing them
                to the queue. Can result in resolving problems in further downstream collections. Necessary for
                branching decisions.
            argv:
                The argument vector being passed to the solution.

        """

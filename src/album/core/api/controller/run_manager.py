from abc import ABCMeta, abstractmethod


class IRunManager:
    """Interface managing the running process of a solution.

    A solution is executed in its target environment which is created during installation. This class performs all
    operations necessary to run a solution. Resolving of a solution in all configured catalogs,
    dependency checking, and more.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def run(self, solution_to_resolve: str, run_immediately=False, argv=None):
        """Function corresponding to the `run` subcommand of `album`."""
        raise NotImplementedError

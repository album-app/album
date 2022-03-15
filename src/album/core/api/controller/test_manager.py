from abc import ABCMeta, abstractmethod


class ITestManager:
    """Interface managing testing routine of a solution. Similar to the installation process, a configured \"test \"
    routine of a solution is executed in the target environment (The conda environment the solution lives in).
    Solutions must be installed to run their testing routine."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def test(self, solution_to_resolve: str, args=None):
        """Function corresponding to the `test` subcommand of `album`."""
        raise NotImplementedError

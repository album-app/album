"""Interface handling the installation and uninstallation process of a solution."""

from abc import ABCMeta, abstractmethod
from typing import List, Optional

from album.runner.core.api.model.solution import ISolution


class IInstallManager:
    """Interface handling the installation and uninstallation process of a solution.

    Installing or uninstalling a solution holds the lock of that solution, see
    ISolutionHandler.get_solution_lock. Installing it also holds the locks of its
    parents, whose environment it is installed into. Album processes and threads using
    the same base path install other solutions at the same time, they only wait for
    each other when they install or uninstall the same solution or one of its parents.
    They wait for at most DefaultValues.install_lock_timeout_in_seconds before raising a
    TimeoutError. Installing a solution that is already installed does not wait.

    An installation that fails or is interrupted is removed right away. One left
    unfinished by an album process that ended before finishing it (e.g. it was killed)
    is removed by the next installation, see clean_unfinished_installations.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def clean_unfinished_installations(self):
        """Remove traces of any installation that was started but not finished.

        Installations in progress in another album process or thread hold the lock of
        their solution and are not removed. The lock is released when the process ends,
        so the installations removed are those of processes that ended before finishing.
        """
        raise NotImplementedError

    @abstractmethod
    def install(
        self,
        solution_to_resolve: str,
        allow_recursive: bool = False,
        argv: Optional[List[str]] = None,
    ) -> ISolution:
        """Install an album solution.

        Args:
            solution_to_resolve:
                The path, DOI or group-name-version information of the solution
                to install.
            allow_recursive:
                Allow the environment of the solution to install a different album
                version than the running one (album in album). Without it, such a
                solution is not installed (ValueError). The same or an unversioned
                album is always allowed, with a warning. A solution with a parent runs
                in the environment of its parent, so there it applies to the parent.
            argv:
                Not used. The install routine of a solution takes no arguments.
                Kept so that existing positional and keyword calls keep working.

        """
        raise NotImplementedError

    @abstractmethod
    def uninstall(
        self,
        solution_to_resolve: str,
        rm_dep: bool = False,
        argv: Optional[List[str]] = None,
    ):
        """Remove a solution from the disk.

         Thereby uninstalling its environment and deleting all its downloads.

        Args:
            solution_to_resolve:
                The path, DOI or group-name-version information of the solution to remove.
            rm_dep:
                Boolean to indicate whether to remove parents too.
            argv:
                Not used. The uninstall routine of a solution takes no arguments.
                Kept so that existing positional and keyword calls keep working.

        """
        raise NotImplementedError

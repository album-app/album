"""Interface handling the installation and uninstallation process of a solution."""
from abc import ABCMeta, abstractmethod
from typing import List, Optional

from album.runner.core.api.model.solution import ISolution


class IInstallManager:
    """Interface handling the installation and uninstallation process of a solution."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def clean_unfinished_installations(self):
        """Remove traces of any installation that was started but not finished."""
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
                album is always allowed, with a warning. Has no effect for a
                solution with a parent: the parent environment is checked without it.
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

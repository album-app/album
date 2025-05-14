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
        """Install an album solution."""
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
            argv:
                Arguments which should be appended to the script call.
            solution_to_resolve:
                The path, DOI or group-name-version information of the solution to remove.
            rm_dep:
                Boolean to indicate whether to remove parents too.

        """
        raise NotImplementedError

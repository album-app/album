from abc import ABCMeta, abstractmethod

from album.core.api.model.resolve_result import IResolveResult
from album.runner.core.api.model.coordinates import ICoordinates


class IInstallManager:
    """Interface handling the installation and uninstallation process of a solution.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def install(self, resolve_solution, argv=None):
        """Function corresponding to the `install` subcommand of `album`."""
        raise NotImplementedError

    @abstractmethod
    def install_from_catalog_coordinates(self, catalog_name: str, coordinates: ICoordinates,
                                         argv=None) -> IResolveResult:
        """API entry point for installation from a specific catalog"""
        raise NotImplementedError

    @abstractmethod
    def install_from_coordinates(self, coordinates: ICoordinates, argv=None) -> IResolveResult:
        """API entry point for installation from any catalog"""
        raise NotImplementedError

    @abstractmethod
    def uninstall(self, resolve_solution, rm_dep=False, argv=None):
        """Removes a solution from the disk. Thereby uninstalling its environment and deleting all its downloads.

        Args:
            argv:
                Arguments which should be appended to the script call
            resolve_solution:
                The path, DOI or group-name-version information of the solution to remove.
            rm_dep:
                Boolean to indicate whether to remove parents too.

        """
        raise NotImplementedError

from abc import ABCMeta, abstractmethod


class IInstallManager:
    """Interface handling the installation and uninstallation process of a solution."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def clean_unfinished_installations(self):
        """Remove traces of any installation that was started but not finished."""
        raise NotImplementedError

    @abstractmethod
    def install(self, solution_to_resolve: str, argv=None):
        """Function corresponding to the `install` subcommand of `album`."""
        raise NotImplementedError

    @abstractmethod
    def uninstall(self, solution_to_resolve: str, rm_dep=False, argv=None):
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

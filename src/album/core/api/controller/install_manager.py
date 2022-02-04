from abc import ABCMeta, abstractmethod


class IInstallManager:
    """Interface handling the installation and uninstallation process of a solution.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def install(self, resolve_solution, argv=None):
        """Function corresponding to the `install` subcommand of `album`."""
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

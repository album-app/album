"""Interface handling the installation and uninstallation process of a solution."""

from abc import ABCMeta, abstractmethod
from typing import Any, Dict, List, Optional

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
        reinstall: bool = False,
        no_conda_lock: bool = False,
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
            reinstall:
                Install the solution again if it is installed: uninstall it and
                install it again from its catalog, or from the file, URL or DOI
                given. A solution installed from a file, URL or DOI and given by its
                coordinates is installed from its copy in the collection.
                The solutions running in its environment are uninstalled and
                installed again with it if they come from a catalog. If one of them
                was installed from a file, URL or DOI, nothing is changed and a
                RuntimeError is raised: album leaves the environment of such a
                solution untouched. Everything is downloaded before anything is
                uninstalled.
            no_conda_lock:
                Solve the environment instead of installing it from the lock file of
                the solution, e.g. when the lock file does not install on this system.
                Not technically replicable, album warns. A solution with a parent runs
                in the environment of its parent, so there it applies to the parent
                if the parent is installed with it.

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

    @abstractmethod
    def upgrade_solutions(
        self, solutions: Optional[List[str]] = None, dry_run: bool = False
    ) -> Dict[str, Any]:
        """Install the latest version of installed solutions, and uninstall what it replaces.

        The catalogs of the solutions are upgraded first, as by `album upgrade`. For each
        solution installed from a catalog, the latest version in that catalog is
        installed if it is newer than the installed ones, and with it its parent. An
        older installed version is uninstalled once no installed solution runs in its
        environment anymore. The newest installed version of a solution always stays: a
        parent the upgraded solutions no longer run in is only uninstalled when a newer
        version of it is installed. Solutions installed from a file, URL or DOI are not
        upgraded.

        Args:
            solutions:
                The installed solutions to upgrade, all of them if None or empty.
            dry_run:
                Only return what would be installed and uninstalled. Which parent a new
                version runs in is only known once it is installed: a new version of a
                parent it brings along is not listed, and an old version it still runs
                in is kept although listed as uninstalled.

        Returns:
            "install" and "uninstall": the solutions installed and uninstalled, as
            catalog:group:name:version. "keep": the older versions that stay, each with
            the solutions running in it ("solution", "used_by"). "unused": installed
            parents no solution runs in anymore. "failed": the installations and
            uninstallations that failed ("solution", "error"). "dry_run": as given.

        """
        raise NotImplementedError

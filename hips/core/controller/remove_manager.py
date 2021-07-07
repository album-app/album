from hips.core import load, pop_active_hips
from hips.core.concept.singleton import Singleton
from hips.core.controller.resolve_manager import ResolveManager
from hips.core.utils.operations.file_operations import force_remove
from hips_runner import logging

module_logger = logging.get_active_logger


class RemoveManager(metaclass=Singleton):
    """Class managing the installed solutions from the catalogs.

    When solutions are not required any more they can be removed, either with their dependencies or without.
    During removal of a solution its environment will be removed and all additional downloads are removed from the disk.

    Attributes:
        resolve_manager:
            Holding all configured catalogs. Resolves inside our outside catalogs.

    """
    # singletons
    resolve_manager = None

    def __init__(self, resolve_manager=None):
        self.resolve_manager = ResolveManager() if not resolve_manager else resolve_manager
        self._active_hips = None

    def remove(self, path, rm_dep):
        """Removes a solution from the disk. Thereby uninstalling its environment and deleting all its downloads.

        Args:
            path:
                The path, DOI or group-name-version information of the solution to remove.
            rm_dep:
                Boolean to indicate whether to remove dependencies too.

        """
        # ToDo: only delete from catalog if the solution is nowhere needed any more
        # Todo: some kind of dependency solving in the catalog. Both ways for resolving
        # if c is going to be deleted - check if c is installed
        # if d is going to be deleted - delete c if possible (no other things installed which depend on c)
        #
        # a
        # ├── b
        # │   └── d <- dependency to c
        # └── c <- d depended on c
        # what if solutions depend on solutions from a different catalog?
        # -> ignore this dependency then?

        try:
            resolve, self._active_hips = self.resolve_manager.resolve_and_load(path, mode="c")
        except ValueError:
            raise ValueError("Solution points to a local file which has not been installed yet. "
                             "Please point to an installation from the catalog or install the solution. "
                             "Aborting...")

        if rm_dep:
            self.remove_dependencies()

        self._active_hips.environment.remove()

        self.remove_disc_content()

        if resolve["catalog"].is_local:
            resolve["catalog"].remove(self._active_hips)

        pop_active_hips()

        module_logger().info("Removed %s!" % self._active_hips['name'])

    def remove_disc_content(self):
        force_remove(self._active_hips.environment.cache_path)
        force_remove(self._active_hips.cache_path_download)
        force_remove(self._active_hips.cache_path_app)
        force_remove(self._active_hips.cache_path_solution)

    def remove_dependencies(self):
        """Recursive call to remove all dependencies"""
        if self._active_hips.dependencies:
            if 'hips' in self._active_hips.dependencies:
                args = self._active_hips.dependencies['hips']
                for hips_dependency in args:
                    # ToDo: need to search through all installed installations if there is another dependency of what
                    #  we are going to delete... otherwise there will nasty resolving errors during runtime
                    hips_dependency_path = self.resolve_manager.catalog_collection.resolve_hips_dependency(
                        hips_dependency, download=False
                    )["path"]
                    self.remove(hips_dependency_path, True)

        if self._active_hips.parent:
            hips_parent_path = self.resolve_manager.catalog_collection.resolve_hips_dependency(
                self._active_hips.parent, download=False
            )["path"]
            self.remove(hips_parent_path, True)

from album.core import pop_active_solution
from album.core.concept.singleton import Singleton
from album.core.controller.catalog_manager import CatalogManager
from album.core.utils.operations.file_operations import force_remove
from album_runner import logging

module_logger = logging.get_active_logger


class RemoveManager(metaclass=Singleton):
    """Class managing the installed solutions from the catalogs.

    When solutions are not required any more they can be removed, either with their dependencies or without.
    During removal of a solution its environment will be removed and all additional downloads are removed from the disk.

    Attributes:
        catalog_manager:
            Holding all configured catalogs. Resolves inside our outside catalogs.

    """
    # singletons
    catalog_manager = None

    def __init__(self):
        self.catalog_manager = CatalogManager()
        self._active_solution = None

    def remove(self, path, rm_dep=False):
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

        resolve, self._active_solution = self.catalog_manager.resolve_require_installation_and_load(path)

        if rm_dep:
            self.remove_dependencies()

        self._active_solution.environment.remove()

        self.remove_disc_content()

        self.catalog_manager.remove_solution(resolve['catalog'], self._active_solution)

        pop_active_solution()

        module_logger().info("Removed %s!" % self._active_solution['name'])

    def remove_disc_content(self):
        force_remove(self._active_solution.environment.cache_path)
        force_remove(self._active_solution.cache_path_download)
        force_remove(self._active_solution.cache_path_app)
        force_remove(self._active_solution.cache_path_solution)

    def remove_dependencies(self):
        """Recursive call to remove all dependencies"""
        if self._active_solution.dependencies:
            if 'album' in self._active_solution.dependencies:
                args = self._active_solution.dependencies['album']
                for dependency in args:
                    # ToDo: need to search through all installed installations if there is another dependency of what
                    #  we are going to delete... otherwise there will nasty resolving errors during runtime
                    dependency_path = self.catalog_manager.resolve_dependency(dependency)["path"]
                    self.remove(dependency_path, True)

        if self._active_solution.parent:
            parent_path = self.catalog_manager.resolve_dependency(self._active_solution.parent)["path"]
            self.remove(parent_path, True)

from album.core import pop_active_solution
from album.core.concept.singleton import Singleton
from album.core.controller.collection_manager import CollectionManager
from album.core.utils.operations.file_operations import force_remove
from album_runner import logging

module_logger = logging.get_active_logger


class RemoveManager(metaclass=Singleton):
    """Class managing the installed solutions from the catalogs.

    When solutions are not required any more they can be removed, either with their dependencies or without.
    During removal of a solution its environment will be removed and all additional downloads are removed from the disk.

    Attributes:
        collection_manager:
            Holding all configured catalogs. Resolves inside our outside catalogs.

    """
    # singletons
    collection_manager = None

    def __init__(self):
        self.collection_manager = CollectionManager()

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

        resolve_result = self.collection_manager.resolve_require_installation_and_load(path)

        if rm_dep:
            self.remove_dependencies(resolve_result.active_solution)

        resolve_result.active_solution.environment.remove()

        self.remove_disc_content(resolve_result.active_solution)

        self.collection_manager.solutions().remove_solution(resolve_result.catalog, resolve_result.active_solution)

        pop_active_solution()

        module_logger().info("Removed %s!" % resolve_result.active_solution['name'])

    @staticmethod
    def remove_disc_content(solution):
        force_remove(solution.environment.cache_path)
        force_remove(solution.cache_path_download)
        force_remove(solution.cache_path_app)
        force_remove(solution.cache_path_solution)

    def remove_dependencies(self, solution):
        """Recursive call to remove all dependencies"""
        if solution.dependencies:
            if 'album' in solution.dependencies:
                args = solution.dependencies['album']
                for dependency in args:
                    # ToDo: need to search through all installed installations if there is another dependency of what
                    #  we are going to delete... otherwise there will nasty resolving errors during runtime
                    dependency_path = self.collection_manager.resolve_dependency(dependency)["path"]
                    self.remove(dependency_path, True)

        if solution.parent:
            parent_path = self.collection_manager.resolve_dependency(solution.parent)["path"]
            self.remove(parent_path, True)

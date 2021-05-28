import shutil

from hips.core import load, pop_active_hips
from hips.core.model import logging
from hips.core.model.configuration import HipsCatalogConfiguration

module_logger = logging.get_active_logger


def remove(args):
    HipsRemover(args.path, args.remove_deps).remove()


class HipsRemover:
    catalog_configuration = None

    def __init__(self, path, rm_dep):
        self.catalog_configuration = HipsCatalogConfiguration()

        self.path = path
        self.rm_dep = rm_dep
        self.active_hips = None

    def remove(self):
        # ToDo: only delete from catalog if the solution is nowhere needed any more
        # Todo: some kind of dependency solving in the catalog. Both ways for resolving
        # if c is going to be deleted - check if c is installed
        # if d is going to be deleted - delete c if possible (no other things installed which depend on c)
        #
        # a
        # ├── b
        # │   └── d <- dependency to c
        # └── c <- d depended on c
        # what if solutions depend oon solutions from a different catalog?
        # -> ignore this dependency then?

        resolve = self.catalog_configuration.resolve_from_str(self.path)
        self.active_hips = load(resolve["path"])

        if not resolve["catalog"]:
            # check if solution pointing to a path is installed...
            resolve = self.catalog_configuration.resolve(self.active_hips.get_hips_deploy_dict())

            if not resolve or not resolve["catalog"]:
                raise IndexError("Solution points to a local file which has not been installed yet. "
                                 "Please point to an installation from the catalog or install the solution. "
                                 "Aborting...")

        if self.rm_dep:
            self.remove_dependencies()

        self.active_hips.environment.remove()

        path = self.catalog_configuration.configuration.get_cache_path_hips(self.active_hips)
        shutil.rmtree(path, ignore_errors=True)

        if resolve["catalog"].is_local:
            resolve["catalog"].remove(self.active_hips)

        pop_active_hips()

        module_logger().info("Removed %s!" % self.active_hips['name'])

    def remove_dependencies(self):
        """Recursive call to remove all dependencies"""
        if self.active_hips.dependencies:
            if 'hips' in self.active_hips.dependencies:
                args = self.active_hips.dependencies['hips']
                for hips_dependency in args:
                    # ToDo: need to search through all installed installations if there is another dependency of what
                    #  we are going to delete... otherwise there will nasty resolving errors during runtime
                    hips_dependency_path = self.catalog_configuration.resolve_hips_dependency(hips_dependency)["path"]
                    remove(hips_dependency_path)

        if self.active_hips.parent:
            hips_parent_path = self.catalog_configuration.resolve_hips_dependency(self.active_hips.parent)["path"]
            remove(hips_parent_path)

import json
from pathlib import Path

from hips.core.model.configuration import HipsConfiguration

from hips.ci.zenodo_api import ZenodoAPI, ZenodoDefaultUrl
from hips.core.model.catalog_index import CatalogIndex
from hips.core.model.default_values import HipsDefaultValues
from hips.core.utils.operations.file_operations import force_remove, unzip_archive
from hips.core.utils.operations.git_operations import download_repository
from hips.core.utils.operations.url_operations import download_resource
from hips_runner import logging

module_logger = logging.get_active_logger


# todo: how to do that efficiently? Download the whole catalog? Or only the index and then the corresp.
#  solutions whenever they are used?
def get_index_src(src):
    """Gets the download link for an index."""
    # todo: "main" is still hardcoded! :(
    return src.strip("git").strip(".") + "/-/raw/main/%s" \
           % HipsDefaultValues.catalog_index_file_name.value


# todo: this is not good! Think of smth. clever here
def get_solution_src(src, grp, name, version):
    """Gets the download link for a solution in an index."""
    # todo: "main" is still hardcoded! :(
    return src.strip("git").strip(".") + "/-/raw/main/solutions/%s/%s/%s/%s" \
           % (grp, name, version, "%s%s%s%s" % (grp, name, version, ".zip"))


class Catalog:
    """Class handling a Catalog.

    A Hips catalog contains solution files. These files are python scripts which can be interpreted by the hips
    framework and implement a routine for solving a problem of any kind. The Catalog has an index where the solution
    files and its metadata are stored in a hierarchical way. This class brings all the functionality to resolve, add,
    remove solutions from a Catalog, wheras resolving refers to the act of looking up, if a solution exists in the
    catalog. A catalog can be local or remote. If the catalog is remote, solutions cannot be
    added or removed to/from it. (see deploy for context)

    Attributes:
        id:
            The ID of the catalog. Usually a string. Can be compared to a name.
        src:
            The online src of the catalog. Usually a gitlab/github link. If none set the catalog is local.
        catalog_index:
            The Index object of the catalog. A tree like structure.
        is_local:
            Boolean indicating whether the catalog is remote or local.
        path:
            The path to the catalog on the disk.
        index_path:
            The path to the catalog index on the disk. Relative to the path attribute.

    """

    # default prefix how to organize solutions. gnv = Group Name Version folder structure.
    doi_solution_prefix = HipsDefaultValues.cache_path_doi_solution_prefix.value
    gnv_solution_prefix = HipsDefaultValues.cache_path_solution_prefix.value

    def __init__(self, catalog_id, path, src=None):
        """Init routine.

        Args:
            catalog_id:
                The ID of the catalog.
            path:
                The absolute path to the catalog.
            src:
                The source of the catalog (Default: None)
        """
        self.id = catalog_id
        self.src = src
        self.catalog_index = None
        self.is_local = True
        self.path = Path(path)
        self.index_path = self.path.joinpath(HipsDefaultValues.catalog_index_file_name.value)

        # initialize the index
        self.load_index()

    def resolve(self, group, name, version, download=True):
        """Resolves (also: finds, looks up) a hips in the catalog and returning the absolute path to the solution file.

        Args:
            group:
                The group where the solution belongs to.
            name:
                The name of the solution
            version:
                The version of the solution
            download:
                Case True: downloads the solution if not already cached.
                Case False: raises FileNotFoundError if not cached
                (Default: True)

        Returns: the path to the solution file.

        """
        tree_leaf_node = self.catalog_index.resolve_hips_by_name_version_and_group(name, version, group)

        if tree_leaf_node:
            path_to_solution = self.get_solution_file(group, name, version)

            if not path_to_solution.is_file():
                if self.is_local or not download:
                    raise FileNotFoundError(
                        "Could resolve the solution, but file %s could not be found!"
                        " Please reinstall the solution!" % path_to_solution)
                if hasattr(tree_leaf_node, "doi"):
                    path_to_solution = self.download_solution_via_doi(getattr(tree_leaf_node, "doi"), name)
                else:
                    path_to_solution = self.download_solution(group, name, version)

            return path_to_solution

        return None  # could not resolve

    def resolve_doi(self, doi, download=True):
        """Resolves a hips via doi. Returns the absolute path to the solution.

        Args:
            doi:
                The doi of the solution
            download:
                Case True: downloads the solution if not already cached.
                Case False: raises FileNotFoundError if not cached
                (Default: True)

        Returns:
            Absolute path to the solution file.

        Raises:
            FileNotFoundError: If download=False and resolved solution is not already cached.

        """
        tree_leaf_node = self.catalog_index.resolve_hips_by_doi(doi)

        if tree_leaf_node:
            path_to_solution = self.get_doi_cache_file(doi)

            # file already cached
            if path_to_solution.is_file():
                return path_to_solution
            elif not download:
                raise FileNotFoundError(
                    "Could resolve the solution, but file %s could not be found!"
                    " Please reinstall the solution!" % path_to_solution)
            else:
                return self.download_solution_via_doi(doi, getattr(tree_leaf_node, "doi"))

        return None  # could not resolve

    def list_installed(self):
        """ Lists all installed solutions in the catalog, thereby iterating over downloaded solutions.

        Returns:
            list if dictionaries. Each list entry corresponds to a solution with "group", "name", "version" set.

        """
        installed_solutions = []

        # search through all installed doi solutions
        installed_doi_path = self.path.joinpath(self.doi_solution_prefix)
        if installed_doi_path.is_dir():
            for directory in installed_doi_path.iterdir():
                installed_solutions.append(self.doi_to_grp_name_version(directory.name))

        # search through all installed solutions without doi
        for grp_dir in self.path.joinpath(self.gnv_solution_prefix).iterdir():
            for solution_dir in grp_dir.iterdir():
                for version_dir in solution_dir.iterdir():
                    installed_solutions.append(
                        self.get_grp_name_version_from_file_structure(
                            grp_dir.name, solution_dir.name, version_dir.name
                        )
                    )

        return sorted(installed_solutions, key=lambda k: k["name"])

    def get_grp_name_version_from_file_structure(self, grp_dir, solution_dir, version_dir):
        """Resolves a solution via its group, name, version and returns their values as a dictionary.

        Args:
            grp_dir:
                The name of the group directory
            solution_dir:
                The name of the solution directory
            version_dir:
                The name of the version directory

        Returns:
            dict holding the metadata of the solution which is supposed to live in the catalog.

        Raises:
             RuntimeError if the solution cannot be found in the catalog, although the folder structure for it exists.

        """
        tree_leaf_node = self.catalog_index.resolve_hips_by_name_version_and_group(solution_dir, version_dir, grp_dir)
        if not tree_leaf_node:
            raise RuntimeError("Folder structure is broken! Could not resolve solution %s in index!" % solution_dir)
        return {
            "group": tree_leaf_node.solution_group,
            "name": tree_leaf_node.solution_name,
            "version": tree_leaf_node.solution_version,
        }

    def doi_to_grp_name_version(self, doi):
        """Resolves a solution via its DOI and returns a dictionary of their group, name, version.

        Args:
            doi:
                The DOI of the solution

        Returns:
            dict holding group, name, version metadata information of the solution.

        Raises:
             RuntimeError if the solution cannot be found in the catalog,
             although the DOI folder structure for it exists.

        """

        tree_leaf_node = self.catalog_index.resolve_hips_by_doi(doi)
        if not tree_leaf_node:
            raise RuntimeError("Folder structure is broken! Could not resolve doi %s in index!" % doi)
        return {
            "group": tree_leaf_node.solution_group,
            "name": tree_leaf_node.solution_name,
            "version": tree_leaf_node.solution_version,
        }

    def get_solution_path(self, g, n, v):
        """Gets the cache path of a solution given its group, name and version. Base path all other files live in.

        Args:
            g:
                The group affiliation of the solution.
            n:
                The name of the solution.
            v:
                The version of the solution.

        Returns:
            The absolute path to the cache folder of the solution.

        """
        return self.path.joinpath(HipsConfiguration.get_solution_path_suffix(g, n, v))

    def get_solution_file(self, g, n, v):
        """Gets the file to the solution.py file of the extracted solution.zip living inside the catalog.

        Args:
            g:
                The group affiliation of the solution.
            n:
                The name of the solution.
            v:
                The version of the solution.

        Returns:
            The path where the file is supposed to be once the zip is extracted during installation.

        """
        p = self.get_solution_path(g, n, v).joinpath(HipsDefaultValues.solution_default_name.value)

        return p

    def get_solution_zip(self, g, n, v):
        """Gets the cache file of a solution given its group, name and version living inside the catalog.

        Args:
            g:
                The group affiliation of the solution.
            n:
                The name of the solution.
            v:
                The version of the solution.

        Returns:
            The absolute path to the solution.py cache file.

        """
        return self.get_solution_path(g, n, v).joinpath(self.get_zip_name(g, n, v))

    def get_solution_zip_suffix(self, g, n, v):
        """Gets the cache suffix of a solution given its group, name and version living inside the catalog.

        Args:
            g:
                The group affiliation of the solution.
            n:
                The name of the solution.
            v:
                The version of the solution.

        Returns:
            The absolute path to the cache folder of the solution.

        """
        return Path("").joinpath(HipsConfiguration.get_solution_path_suffix(g, n, v), self.get_zip_name(g, n, v))

    @staticmethod
    def get_zip_name(g, n, v):
        return "_".join([g, n, v]) + ".zip"

    def get_doi_cache_file(self, doi):
        """Gets the cache path of a solution given a doi.

        Args:
            doi:
                The DOI of the solution.

        Returns:
            The absolute path to the DOI solution file

        """
        return self.path.joinpath(self.doi_solution_prefix, doi)

    # todo: write tests
    def download_solution_via_doi(self, doi, solution_name):
        """Downloads the solution via its doi.

        Args:
            doi:
                The DOI of the solution.
            solution_name:
                The name of the solution

        Returns:
            The absolute path of the downloaded solution.

        Raises:
            RuntimeError if the solution cannot be found in the online resource
                         if the DOI is not unique.

        """
        raise NotImplementedError
        # Todo: replace with non-sandbox version
        zenodo_api = ZenodoAPI(ZenodoDefaultUrl.sandbox_url.value, None)

        # todo: maybe there is a nicer way than parsing stuff from the DOI?
        record_id = doi.split(".")[-1]
        record_list = zenodo_api.records_get(record_id)

        if not record_list:
            raise RuntimeError("Could not receive solution from doi %s. Aborting..." % doi)

        if len(record_list) > 1:
            raise RuntimeError("Doi %s is not unique. Aborting..." % doi)

        record = record_list[0]

        url = record.files[solution_name].get_download_link()

        download_resource(url, self.get_doi_cache_file(doi))

        return self.path.joinpath(self.doi_solution_prefix, doi)

    def download_solution(self, group, name, version):
        """Downloads a solution from the catalog to the local resource.

        Args:
            group:
                The group affiliation of the solution.
            name:
                The name of the solution.
            version:
                The version of the solution.

        Returns:
            The absolute path of the downloaded solution.

        """
        url = get_solution_src(self.src, group, name, version)

        solution_zip_file = self.get_solution_zip(group, name, version)
        download_resource(url, solution_zip_file)

        solution_zip_path = unzip_archive(solution_zip_file)
        solution_path = solution_zip_path.joinpath(HipsDefaultValues.solution_default_name.value)

        return solution_path

    def load_index(self):
        """Loads the index from file or src. If a file and src exists routine tries to update the index."""
        if self.index_path.is_file() or self.src is None:
            # load catalog from already cached file
            if self.src:
                self.refresh_index()
            self.catalog_index = CatalogIndex(self.id, self.index_path)
        else:
            # load catalog from remote src
            self.download_index()
            self.catalog_index = CatalogIndex(self.id, self.index_path)
        self.is_local = True

        if self.src:
            self.is_local = False

    def refresh_index(self):
        """Routine to refresh the catalog index. (actively calling the src)"""
        if not self.src:
            self.catalog_index = CatalogIndex(self.id, self.index_path)
            return True

        try:
            self.download_index()
        except AssertionError:
            module_logger().warning("Could not refresh index. Source invalid!")
            return False
        except ConnectionError:
            module_logger().warning("Could not refresh index. Connection error!")
            return False
        except Exception as e:
            module_logger().warning("Could not refresh index. Unknown reason!")
            module_logger().warning(e)
            return False

        self.catalog_index = CatalogIndex(self.id, self.index_path)
        return True

    def add(self, active_hips, force_overwrite=False):
        """Adds an active hips_object to the index.

        Args:
            active_hips:
                The active hips object (also: solution object, see HipsClass) to add to the catalog.
            force_overwrite:
                When True forces adding a solution which already exists in the catalog. Only valid for solutions without
                DOI. (Default: False)

        Raises:
            RuntimeError when the DOI metadata information of a hips object already exists in the catalog.
                         when the solution already exists and force_overwrite is False.

        """
        node_attrs = active_hips.get_hips_deploy_dict()

        if hasattr(active_hips, "doi"):
            node_attrs["doi"] = getattr(active_hips, "doi")
            if self.catalog_index.resolve_hips_by_doi(node_attrs["doi"]) is not None:
                if force_overwrite:
                    module_logger().warning("Solution already exists! Overwriting...")
                else:
                    raise RuntimeError("DOI already exists in Index! Aborting...")

        if hasattr(active_hips, "deposit_id"):
            node_attrs["deposit_id"] = getattr(active_hips, "deposit_id")

        if self.catalog_index.resolve_hips_by_name_version_and_group(
                node_attrs["name"], node_attrs["version"], node_attrs["group"]
        ) is not None:
            if force_overwrite:
                module_logger().warning("Solution already exists! Overwriting...")
            else:
                raise RuntimeError("Solution already exists in Index! Aborting...")

        self.catalog_index.update(node_attrs)
        self.catalog_index.save()

    def remove(self, active_hips):
        """Removes a solution from a catalog. Only for local catalogs.

        Args:
            active_hips:
                The active hips object (also: solution object, see HipsClass) to remove from the catalog.

        """
        if self.is_local:
            node_attrs = active_hips.get_hips_deploy_dict()

            node = self.catalog_index.resolve_hips_by_name_version_and_group(
                node_attrs["name"], node_attrs["version"], node_attrs["group"]
            )
            if node:
                node.parent = None
                self.catalog_index.save()
            else:
                module_logger().warning("Solution not installed! Doing nothing...")
        else:
            module_logger().warning("Cannot remove entries from a remote catalog! Doing nothing...")

    def visualize(self):
        """Visualizes the catalog on the command line"""
        self.catalog_index.visualize()

    def download_index(self):
        """Downloads the index file of the catalog."""
        src = get_index_src(self.src)

        download_resource(src, self.index_path)

        with open(self.index_path, "r") as f:
            try:
                json.load(f)
            except ValueError as e:
                raise ValueError("Wrong index format!") from e

    def download(self, path=None, force_download=False):
        """Downloads the whole catalog from its source. Used for deployment.

        Args:
            force_download:
                Boolean, indicates whether to force delete content of path or not
            path:
                The path to download to (optional). Catalog path is taken if no path specified.

        Returns:
            The repository object of the catalog

        """
        path = Path(path) if path else self.path

        if force_download:
            force_remove(path)

        module_logger().debug("Download catalog %s to the path %s..." % (self.id, str(path)))

        if not self.is_local:
            repo = download_repository(self.src, str(path))

            return repo

        module_logger().warning("Cannot download a local catalog! Skipping...")

        return None

    def __len__(self):
        return len(self.catalog_index)

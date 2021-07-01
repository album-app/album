import json
import shutil
from pathlib import Path

import anytree
from anytree import RenderTree, Node
from anytree.exporter import JsonExporter, DictExporter
from anytree.importer import JsonImporter

from hips.ci.zenodo_api import ZenodoAPI, ZenodoDefaultUrl
from hips.core.model.default_values import HipsDefaultValues
from hips.core.utils.operations.file_operations import write_dict_to_json, remove_warning_on_error, unzip_archive
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
            path_to_solution = self.get_solution_cache_file(group, name, version)

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

    def get_solution_cache_file(self, group, name, version):
        """Gets the file to the solution.py file of the extracted solution.zip

        Args:
            group:
                The group affiliation of the solution.
            name:
                The name of the solution.
            version:
                The version of the solution.

        Returns:
            The path where the file is supposed to be once the zip is extracted during installation.

        """
        p = self.get_solution_cache_path(group, name, version)
        return p.joinpath(HipsDefaultValues.solution_default_name.value)

    def get_solution_cache_zip(self, group, name, version):
        """Gets the cache file of a solution given its group, name and version.

        Args:
            group:
                The group affiliation of the solution.
            name:
                The name of the solution.
            version:
                The version of the solution.

        Returns:
            The absolute path to the solution.py cache file.

        """
        return self.get_solution_cache_path(group, name, version).joinpath(
            "_".join([group, name, version]) + ".zip"
        )

    def get_solution_cache_path(self, group, name, version):
        """Gets the cache path of a solution given its group, name and version.

        Args:
            group:
                The group affiliation of the solution.
            name:
                The name of the solution.
            version:
                The version of the solution.

        Returns:
            The absolute path to the cache folder of the solution.

        """
        return self.path.joinpath(self.gnv_solution_prefix, group, name, version)

    def get_solution_cache_zip_suffix(self, group, name, version):
        """Gets the cache suffix of a solution given its group, name and version.

        Args:
            group:
                The group affiliation of the solution.
            name:
                The name of the solution.
            version:
                The version of the solution.

        Returns:
            The absolute path to the cache folder of the solution.

        """
        return Path("").joinpath(
            self.gnv_solution_prefix, group, name, version, "_".join([group, name, version]) + ".zip"
        )

    def get_solution_cache_zip_folder_suffix(self, group, name, version):
        """Gets the cache suffix of a solution given its group, name and version.

        Args:
            group:
                The group affiliation of the solution.
            name:
                The name of the solution.
            version:
                The version of the solution.

        Returns:
            The absolute path to the cache folder of the solution.

        """
        return Path("").joinpath(
            self.gnv_solution_prefix, group, name, version
        )

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

        solution_zip_file = self.get_solution_cache_zip(group, name, version)
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
            remove_warning_on_error(path)

        module_logger().debug("Download catalog %s to the path %s..." % (self.id, str(path)))

        if not self.is_local:
            repo = download_repository(self.src, str(path))

            return repo

        module_logger().warning("Cannot download a local catalog! Skipping...")

        return None

    def __len__(self):
        return len(self.catalog_index)


class CatalogIndex:
    """Class handling the Index of a catalog. Holds a tree with meta information on every solution in the catalog.

    Attributes:
        path:
            The absolute path to the index file.
        index:
            The index itself.

    """

    def __init__(self, name, path, index=None):
        """Init routine.

        Args:
            name:
                The name of the catalog.
            path:
                The path to the index file.
            index:
                The index itself. If None will be loaded from path. (Default: None)

        """
        self.path = Path(path)
        self.index = Node(name, **{"version": "0.1.0"})
        if index:
            self.index = index
        else:
            self.load(path)

    @staticmethod
    def _find_node_by_name(search_start_node, name, maxlevel=None):
        """Searches for a node with a given name. Starts searching at a node given."""
        if maxlevel:
            return anytree.search.find(search_start_node, filter_=lambda node: node.name == name, maxlevel=maxlevel)
        else:
            return anytree.search.find(search_start_node, filter_=lambda node: node.name == name)

    @staticmethod
    def _find_all_nodes_by_name(search_start_node, name):
        """Searches for all node with a given name. Starts searching at a node given."""
        return anytree.search.findall(search_start_node, filter_=lambda node: node.name == name)

    @staticmethod
    def _find_node_by_name_and_version(search_start_node, name, version, maxlevel=None):
        """Searches for a node with a given name and version. Starts searching at a node given."""
        solution_node_name = CatalogIndex._find_node_by_name(search_start_node, name, maxlevel)
        if not solution_node_name:
            return None
        return CatalogIndex._find_node_by_name(solution_node_name, version, maxlevel)

    @staticmethod
    def _find_node_by_name_and_group(search_start_node, name, group, maxlevel=None):
        """Searches for a node with a given name and group. Starts searching at a node given."""
        group_node = CatalogIndex._find_node_by_name(search_start_node, group, maxlevel)
        if not group_node:
            return None
        return CatalogIndex._find_node_by_name(group_node, name, maxlevel)

    @staticmethod
    def _find_node_by_name_version_and_group(search_start_node, name, version, group):
        """Searches for a node with a given name, version and group. Starts searching at a node given"""
        group = CatalogIndex._find_node_by_name(search_start_node, group, maxlevel=2)
        if not group:
            return None
        return CatalogIndex._find_node_by_name_and_version(group, name, version, maxlevel=2)

    @staticmethod
    def _find_all_nodes_by_attribute(search_start_node, attribute_value, attribute_name):
        """Searches for all node having a certain attribute value of a given attribute name.
        Starts searching at a node given"""

        return anytree.search.findall_by_attr(search_start_node, value=attribute_value, name=attribute_name)

    @staticmethod
    def __set_group_name_version(node_attrs):
        """Extracts group, name, version information from the attributes of the solution to add to the index. """

        try:
            group = node_attrs.pop("group")  # conflicts with the group node
            node_attrs["solution_group"] = group
        except KeyError as e:
            raise KeyError("Group not specified! Cannot add solution to index! Aborting...") from e

        try:
            name = node_attrs.pop("name")  # conflicts with the name node
            node_attrs["solution_name"] = name
        except KeyError as e:
            raise KeyError("Name not specified! Cannot add solution to index! Aborting...") from e

        try:
            version = node_attrs.pop("version")  # conflicts with the version node
            node_attrs["solution_version"] = version
        except KeyError as e:
            raise KeyError("Version not specified! Cannot add solution to index! Aborting...") from e

        return node_attrs, group, name, version

    def load(self, index_file_path):
        """Loads the catalog index from disk.

        Args:
            index_file_path:
                The path to the index file of the catalog.

        """
        self.path = Path(index_file_path)

        if self.path.is_file():
            if self.path.stat().st_size > 0:
                importer = JsonImporter()
                with open(index_file_path) as json_file:
                    self.index = importer.read(json_file)
            else:
                module_logger().warning("File contains no content!")
        else:
            Path(index_file_path).parent.mkdir(parents=True, exist_ok=True)
            Path(index_file_path).touch()

        return self.index

    def update(self, node_attrs):
        """Updates a catalog to include a solution as a node with the attributes given.
         Updates exiting nodes if node already present in tree.

        Args:
            node_attrs:
                The dictionary holding the solution attributes. Must hold group, name, version.

        Returns:
            The new node in the index.

        """
        node_attrs, group, name, version = self.__set_group_name_version(node_attrs)

        group_node = self._find_node_by_name(self.index, group, maxlevel=2)
        if not group_node:
            module_logger().debug("Group \"%s\" not yet in index, adding..." % group)
            group_node = anytree.Node(group, parent=self.index)

        solution_node_name = self._find_node_by_name(group_node, name, maxlevel=2)  # starting to search from group node
        if not solution_node_name:
            module_logger().debug("Solution \"%s\" not yet in index, adding..." % name)
            solution_node_name = anytree.Node(name, parent=group_node)

        solution_node_version = self._find_node_by_name(solution_node_name, version, maxlevel=2)
        if solution_node_version:  # check if there is already such a version
            module_logger().debug("Solution \"%s\" with version \"%s\" in group \"%s\" already exists. Updating..." %
                                  (name, group, version))
            solution_node_version.parent = None  # remove from tree

        # adds a new version to the solution node
        solution_node_version = anytree.Node(version, parent=solution_node_name, **node_attrs)

        module_logger().info(
            "Added solution \"%s\" with version \"%s\" in group \"%s\" to the index..." % (name, version, group)
        )

        return solution_node_version

    def save(self, path=None):
        """Saves a catalog to disk. Saves it to a certain path if given. If none given default path is taken.

        Args:
            path:
                Optional path to store the index to.

        """
        if path:
            self.path = Path(path)

        module_logger().info("Saving index to path: %s..." % self.path)

        exporter = JsonExporter(indent=2, sort_keys=True)
        with open(self.path, 'w+') as f:
            f.write(exporter.export(self.index))

    def visualize(self):
        """Shows the index content on the command line."""
        if self.index is None:
            module_logger().info("Empty catalog!")
            print("Empty catalog")
        else:
            for pre, _, node in RenderTree(self.index):
                module_logger().info("%s%s" % (pre, node.name))
                print("%s%s" % (pre, node.name))

    def get_leaves_dict_list(self):
        """Get a list of the dictionary of all leaves in the index.

        Returns:
                all leaves of the catalog index.

        """
        leaves = self.index.leaves
        dict_exporter = DictExporter()
        leaves_dict_list = []
        for leaf in leaves:
            if leaf.depth == 3:  # only add depth 3 nodes (these are solution nodes)
                leaf_dict = dict_exporter.export(leaf)
                leaves_dict_list.append(leaf_dict)
        return leaves_dict_list

    # untested
    def resolve_hips_by_name(self, name):
        search_result_list = []
        for groups in self.index.children:
            search_result = self._find_node_by_name(groups, name)

            if search_result:
                if len(search_result.children) > 1:
                    module_logger().warning("Found several versions! Taking the latest one...")
                # always use the latest version
                search_result_list.append(search_result.children[-1])

        if not search_result_list:
            raise RuntimeError("Could not resolve hips!")

        if len(search_result_list) > 1:
            raise RuntimeError("Found a solution named identical for different groups! Please be more specific!")

        # returns the hips leaf node
        return search_result_list[0]

    # untested
    def resolve_hips_by_name_and_group(self, name, group):
        search_result = self._find_node_by_name_and_group(self.index, name, group, maxlevel=2)

        if search_result:
            if len(search_result.children) > 1:
                module_logger().warning("Found several versions! Taking the latest one...")

        # returns the hips leaf node
        return search_result.children[-1]

    # untested
    def resolve_hips_by_name_and_version(self, name, version):
        search_result_list = []
        for groups in self.index.children:
            # search result in a grp must be unique
            search_result = self._find_node_by_name_and_version(groups, name, version)
            if search_result:
                search_result_list.append(search_result)

        if not search_result_list:
            raise RuntimeError("Could not resolve hips!")

        if len(search_result_list) > 1:
            raise RuntimeError("Found a solution named identical for different groups! Please be more specific!")

        # returns the hips leaf node
        return search_result_list[0]

    def resolve_hips_by_name_version_and_group(self, name, version, group):
        """Resolves a solution by its name, version and group.

        Args:
            group:
                The group affiliation of the solution.
            name:
                The name of the solution.
            version:
                The version of the solution.

        Returns:
            None or a node if found.

        Raises:
             RuntimeError of the node found is not a leaf.

        """
        # result is unique hips leaf node
        node = self._find_node_by_name_version_and_group(self.index, name, version, group)
        if node:
            if node.is_leaf:
                return node
            else:
                raise RuntimeError("Index is broken. Ambiguous results! Please refresh index!")
        return None

    def resolve_hips_by_doi(self, doi):
        """Resolves a solution by its DOI.

        Args:
            doi:
                The doi to resolve for.

        Returns:
            None or a node if any found.

        Raises:
            RuntimeError if the DOI was found more than once.
                         if the node found is not a leaf

        """
        # result is unique hips leaf node
        nodes = self._find_all_nodes_by_attribute(self.index, doi, 'doi')

        if nodes:
            if len(nodes) > 1:
                raise RuntimeError("Found several results for this doi! Doi correct? Try to refresh the index!")
            node = nodes[0]

            if node.is_leaf:
                return node
            else:
                raise RuntimeError("Index is broken. Ambiguous results! Please refresh index!")
        return None

    def export(self, path, export_format="JSON"):
        """Exports the index tree to disk.

        Args:
            path:
                The path to store the export to.
            export_format:
                The format to save to. Choose from ["JSON"]. (Default: JSON)

        Raises:
            RuntimeError if the format is not supported.

        """
        path = Path(path)
        leaves_dict = self.get_leaves_dict_list()

        if export_format == "JSON":
            write_dict_to_json(path, leaves_dict)
        else:
            raise RuntimeError("Unsupported format \"%s\"" % export_format)

    def __len__(self):
        leaves = self.index.leaves
        count = 0
        for leaf in leaves:
            if leaf.depth == 3:  # only add depth 3 nodes (these are solution nodes)
                count += 1

        return count

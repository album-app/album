import json
from pathlib import Path

import anytree
from anytree import RenderTree, Node
from anytree.exporter import JsonExporter, DictExporter
from anytree.importer import JsonImporter

from hips.deploy import get_hips_deploy_dict
from hips.hips_base import HipsDefaultValues
from hips_utils import hips_logging
from hips_utils.operations.git_operations import download_repository
from hips_utils.operations.url_operations import download_resource
from hips_utils.zenodo_api import ZenodoAPI, ZenodoDefaultUrl

module_logger = hips_logging.get_active_logger


# todo: how to do that efficiently? Download the whole catalog? Or only the index and then the corresp.
#  solutions whenever they are used?
def get_index_src(src):
    # todo: replace new_catalog_structure branch with "main"... although "main" is also hardcoded! :(
    return src.strip("git").strip(".") + "/-/raw/new_catalog_structure/%s" \
           % HipsDefaultValues.catalog_index_file_name.value


# todo: this is not good! Think of smth. clever here
def get_solution_src(src, grp, name, version):
    return src.strip("git").strip(".") + "/-/raw/new_catalog_structure/solutions/%s/%s/%s/%s.py" \
           % (grp, name, version, name)


class Catalog:
    """Class handling a Catalog."""

    # default prefix how to organize solutions. gnv = Group Name Version folder structure.
    doi_solution_prefix = "doi_solutions"
    gnv_solution_prefix = "solutions"

    def __init__(self, catalog_id, path, src=None):
        self.id = catalog_id
        self.src = src
        self.catalog_index = None
        self.is_local = True
        self.path = Path(path)
        self.index_path = self.path.joinpath(HipsDefaultValues.catalog_index_file_name.value)

        # initialize the index
        self.load_index()

    def resolve(self, group, name, version):
        """ Resolves a hips in the catalog and returning the absolute path to the solution file.

        Args:
            group:
                The group where the solution belongs to.
            name:
                The name of the solution
            version:
                The version of the solution

        Returns: the path to the solution file.

        """
        tree_leaf_node = self.catalog_index.resolve_hips_by_name_version_and_group(name, version, group)

        if tree_leaf_node:
            path_to_solution = self.get_solution_cache_file(group, name, version)

            if not path_to_solution.is_file():
                if self.is_local:
                    raise FileNotFoundError("Could resolve the solution, but file could not be found!"
                                            " Please reinstall the solution!")
                if hasattr(tree_leaf_node, "doi"):
                    self.download_solution_via_doi(getattr(tree_leaf_node, "doi"), name)
                else:
                    self.download_solution(group, name, version)

            return path_to_solution

        return None  # could not resolve

    def resolve_doi(self, doi):
        """Resolves a hips via doi. Returns the absolute path to the solution.

        Args:
            doi:
                The doi of the solution

        Returns:
            Absolute path to the solution file.
        """
        tree_leaf_node = self.catalog_index.resolve_hips_by_doi(doi)

        if tree_leaf_node:
            path_to_solution = self.get_doi_cache_file(doi)

            # file already cached
            if path_to_solution.is_file():
                return path_to_solution
            else:
                return self.download_solution_via_doi(doi, getattr(tree_leaf_node, "doi"))

        return None  # could not resolve

    def list_installed(self):
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

        return installed_solutions

    def get_grp_name_version_from_file_structure(self, grp_dir, solution_dir, version_dir):
        tree_leaf_node = self.catalog_index.resolve_hips_by_name_version_and_group(grp_dir, solution_dir, version_dir)
        if not tree_leaf_node:
            raise RuntimeError("Folder structure is broken! Could not resolve solution %s in index!" % solution_dir)
        return {
            "group": tree_leaf_node["solution_group"],
            "name": tree_leaf_node["solution_name"],
            "version": tree_leaf_node["solution_version"],
        }

    def doi_to_grp_name_version(self, doi):
        tree_leaf_node = self.catalog_index.resolve_hips_by_doi(doi)
        if not tree_leaf_node:
            raise RuntimeError("Folder structure is broken! Could not resolve doi %s in index!" % doi)
        return {
            "group": tree_leaf_node["solution_group"],
            "name": tree_leaf_node["solution_name"],
            "version": tree_leaf_node["solution_version"],
        }

    def get_solution_cache_file(self, group, name, version):
        """Gets the cache file of a solution given its group, name and version."""
        return self.get_solution_cache_path(group, name, version).joinpath("%s%s" % (name, ".py"))

    def get_solution_cache_path(self, group, name, version):
        """Gets the cache path of a solution given its group, name and version."""
        return self.path.joinpath(self.gnv_solution_prefix, group, name, version)

    def get_doi_cache_file(self, doi):
        """Gets the cache path of a solution given a doi."""
        return self.path.joinpath(self.doi_solution_prefix, doi)

    # todo: write tests
    def download_solution_via_doi(self, doi, solution_name):
        """Downloads the solution via its doi."""
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

    # todo: write tests
    def download_solution(self, group, name, version):
        """Downloads a solution from the catalog to the local resource."""
        url = get_solution_src(self.src, group, name, version)
        download_resource(url, self.path.joinpath(self.gnv_solution_prefix, group, name, version))
        return self.path.joinpath(self.gnv_solution_prefix, group, name, version)

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

    def add_to_index(self, active_hips, force_overwrite=False):
        node_attrs = get_hips_deploy_dict(active_hips)

        if hasattr(active_hips, "doi"):
            node_attrs["doi"] = getattr(active_hips, "doi")
            if self.catalog_index.resolve_hips_by_doi(node_attrs["doi"]) is not None:
                if force_overwrite:
                    module_logger().warning("Soltion already exists! Overwriting...")
                else:
                    raise RuntimeError("DOI already exists in Index! Aborting...")

        if hasattr(active_hips, "deposit_id"):
            node_attrs["deposit_id"] = getattr(active_hips, "deposit_id")

        if self.catalog_index.resolve_hips_by_name_version_and_group(
                node_attrs["name"], node_attrs["version"], node_attrs["group"]
        ) is not None:
            if force_overwrite:
                module_logger().warning("Soltion already exists! Overwriting...")
            else:
                raise RuntimeError("Solution already exists in Index! Aborting...")

        self.catalog_index.update_index(node_attrs)
        self.catalog_index.save_catalog_index()

    def visualize(self):
        self.catalog_index.visualize()

    def download_index(self):

        src = get_index_src(self.src)

        download_resource(src, self.index_path)

        with open(self.index_path, "r") as f:
            try:
                json.load(f)
            except ValueError as e:
                raise ValueError("Wrong index format!") from e

    def download(self):
        """Downloads the whole catalog. Used for deployment."""
        module_logger().debug("Download catalog %s to the path %s..." % (self.id, str(self.path)))
        repo = download_repository(self.src, str(self.path))

        return repo

    def __len__(self):
        return len(self.catalog_index)


class CatalogIndex:
    """Class handling the Index of a catalog. Holds a tree with information on every solution in the catalog."""

    def __init__(self, name, path, index=None):

        self.catalog_index_path = Path(path)
        self.catalog_index = Node(name, **{"version": "0.1.0"})
        if index:
            self.catalog_index = index
        else:
            self.load_catalog_index_from_disk(path)

    @staticmethod
    def _find_node_by_name(search_start_node, name, maxlevel=None):
        """Searches for a node with a given name. Starts searching at a node given"""
        if maxlevel:
            return anytree.search.find(search_start_node, filter_=lambda node: node.name == name, maxlevel=maxlevel)
        else:
            return anytree.search.find(search_start_node, filter_=lambda node: node.name == name)

    @staticmethod
    def _find_all_nodes_by_name(search_start_node, name):
        """Searches for all node with a given name. Starts searching at a node given"""
        return anytree.search.findall(search_start_node, filter_=lambda node: node.name == name)

    @staticmethod
    def _find_node_by_name_and_version(search_start_node, name, version, maxlevel=None):
        """Searches for a node with a given name and version. Starts searching at a node given"""
        solution_node_name = CatalogIndex._find_node_by_name(search_start_node, name, maxlevel)
        if not solution_node_name:
            return None
        return CatalogIndex._find_node_by_name(solution_node_name, version, maxlevel)

    @staticmethod
    def _find_node_by_name_and_group(search_start_node, name, group, maxlevel=None):
        """Searches for a node with a given name and group. Starts searching at a node given"""
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

    def load_catalog_index_from_disk(self, index_file_path):
        """Loads the catalog index from disk.

        Args:
            index_file_path:
                The path to the index file of the catalog.

        """
        self.catalog_index_path = Path(index_file_path)

        if self.catalog_index_path.is_file():
            if self.catalog_index_path.stat().st_size > 0:
                importer = JsonImporter()
                with open(index_file_path) as json_file:
                    self.catalog_index = importer.read(json_file)
            else:
                module_logger().warning("File contains no content!")
        else:
            Path(index_file_path).parent.mkdir(parents=True, exist_ok=True)
            Path(index_file_path).touch()

        return self.catalog_index

    def update_index(self, node_attrs):
        """Updates a catalog to include a solution as a node with the attributes given.
         Updates exiting nodes if node already present in tree.

        Args:
            node_attrs:
                The dictionary holding the solution attributes. Must hold group, name, version.

        Returns:
            The new node in the index

        """
        node_attrs, group, name, version = self.__set_group_name_version(node_attrs)

        group_node = self._find_node_by_name(self.catalog_index, group, maxlevel=2)
        if not group_node:
            module_logger().debug("Group %s not yet in index, adding..." % group)
            group_node = anytree.Node(group, parent=self.catalog_index)

        solution_node_name = self._find_node_by_name(group_node, name, maxlevel=2)  # starting to search from group node
        if not solution_node_name:
            module_logger().debug("Solution %s not yet in index, adding..." % name)
            solution_node_name = anytree.Node(name, parent=group_node)

        solution_node_version = self._find_node_by_name(solution_node_name, version, maxlevel=2)
        if solution_node_version:  # check if there is already such a version
            module_logger().debug("Solution %s with version %s in group %s already exists. Updating..." %
                                  (name, group, version))
            solution_node_version.parent = None  # remove from tree

        # adds a new version to the solution node
        solution_node_version = anytree.Node(version, parent=solution_node_name, **node_attrs)

        module_logger().info("Added solution %s with version %s in group %s to the index..." % (name, group, version))

        return solution_node_version

    def save_catalog_index(self, path=None):
        """Saves a catalog to disk. Saves it to a certain path if given. If none given default path is taken.

        Args:
            path:
                Optional path to store the index to.

        """
        if path:
            self.catalog_index_path = Path(path)

        module_logger().info("Saving index to path: %s..." % self.catalog_index_path)

        exporter = JsonExporter(indent=2, sort_keys=True)
        with open(self.catalog_index_path, 'w+') as f:
            f.write(exporter.export(self.catalog_index))

    def visualize(self):
        """Shows the index content on the command line."""
        if self.catalog_index is None:
            module_logger().info("Empty catalog!")
            print("Empty catalog")
        else:
            for pre, _, node in RenderTree(self.catalog_index):
                module_logger().info("%s%s" % (pre, node.name))
                print("%s%s" % (pre, node.name))

    def get_leaves_dict_list(self):
        """Get a list of the dictionary of all leaves in the index."""
        leaves = self.catalog_index.leaves
        dict_exporter = DictExporter()
        leaves_dict_list = []
        for leaf in leaves:
            if leaf.depth == 3:  # only add depth 3 nodes (these are solution nodes)
                leaf_dict = dict_exporter.export(leaf)
                leaves_dict_list.append(leaf_dict)
        return leaves_dict_list

    # untested
    def resolve_hips_by_name(self, name):
        """Resolves a hips by its name

        Args:
            name:
                The name of the hips

        Returns:

        """
        search_result_list = []
        for groups in self.catalog_index.children:
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
        search_result = self._find_node_by_name_and_group(self.catalog_index, name, group, maxlevel=2)

        if search_result:
            if len(search_result.children) > 1:
                module_logger().warning("Found several versions! Taking the latest one...")

        # returns the hips leaf node
        return search_result.children[-1]

    # untested
    def resolve_hips_by_name_and_version(self, name, version):
        search_result_list = []
        for groups in self.catalog_index.children:
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
        # result is unique hips leaf node
        node = self._find_node_by_name_version_and_group(self.catalog_index, name, version, group)
        if node:
            if node.is_leaf:
                return node
            else:
                raise RuntimeError("Index is broken. Ambiguous results! Please refresh index!")
        return None

    def resolve_hips_by_doi(self, doi):
        # result is unique hips leaf node
        nodes = self._find_all_nodes_by_attribute(self.catalog_index, doi, 'doi')

        if nodes:
            if len(nodes) > 1:
                raise RuntimeError("Found several results for this doi! Doi correct? Try to refresh the index!")
            node = nodes[0]

            if node.is_leaf:
                return node
            else:
                raise RuntimeError("Index is broken. Ambiguous results! Please refresh index!")
        return None

    def __len__(self):
        leaves = self.catalog_index.leaves
        count = 0
        for leaf in leaves:
            if leaf.depth == 3:  # only add depth 3 nodes (these are solution nodes)
                count += 1

        return count

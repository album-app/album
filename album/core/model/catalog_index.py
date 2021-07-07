from pathlib import Path

import anytree
from anytree import RenderTree, Node
from anytree.exporter import JsonExporter, DictExporter
from anytree.importer import JsonImporter

from album.core.utils.operations.file_operations import write_dict_to_json
from album_runner import logging

module_logger = logging.get_active_logger


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
    def resolve_by_name(self, name):
        search_result_list = []
        for groups in self.index.children:
            search_result = self._find_node_by_name(groups, name)

            if search_result:
                if len(search_result.children) > 1:
                    module_logger().warning("Found several versions! Taking the latest one...")
                # always use the latest version
                search_result_list.append(search_result.children[-1])

        if not search_result_list:
            raise RuntimeError("Could not resolve album!")

        if len(search_result_list) > 1:
            raise RuntimeError("Found a solution named identical for different groups! Please be more specific!")

        # returns the album leaf node
        return search_result_list[0]

    # untested
    def resolve_by_name_and_group(self, name, group):
        search_result = self._find_node_by_name_and_group(self.index, name, group, maxlevel=2)

        if search_result:
            if len(search_result.children) > 1:
                module_logger().warning("Found several versions! Taking the latest one...")

        # returns the album leaf node
        return search_result.children[-1]

    # untested
    def resolve_by_name_and_version(self, name, version):
        search_result_list = []
        for groups in self.index.children:
            # search result in a grp must be unique
            search_result = self._find_node_by_name_and_version(groups, name, version)
            if search_result:
                search_result_list.append(search_result)

        if not search_result_list:
            raise RuntimeError("Could not resolve album!")

        if len(search_result_list) > 1:
            raise RuntimeError("Found a solution named identical for different groups! Please be more specific!")

        # returns the album leaf node
        return search_result_list[0]

    def resolve_by_name_version_and_group(self, name, version, group):
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
        # result is unique album leaf node
        node = self._find_node_by_name_version_and_group(self.index, name, version, group)
        if node:
            if node.is_leaf:
                return node
            else:
                raise RuntimeError("Index is broken. Ambiguous results! Please refresh index!")
        return None

    def resolve_by_doi(self, doi):
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
        # result is unique album leaf node
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

import operator

from hips.core.concept.singleton import Singleton

from hips.core.model.catalog_collection import HipsCatalogCollection
from hips_runner import logging

module_logger = logging.get_active_logger


class SearchManager(metaclass=Singleton):
    """Class responsible for searching with keywords through all configured catalogs. Solutions must not be installed
    to be findable in a search request.

     Attributes:
         catalog_collection:
            Holds all the catalogs of the HIPS framework installation.

    """
    # singletons
    catalog_collection = None

    def __init__(self, catalog_collection=None):
        self.catalog_collection = HipsCatalogCollection() if not catalog_collection else catalog_collection

    def search(self, keywords):
        """Function corresponding to the `search` subcommand of `hips`.

        Searches through hips catalogs to find closest matching hip solution.

        """
        module_logger().debug("Searching with following arguments %s..." % ", ".join(keywords))

        search_index = self.catalog_collection.get_search_index()
        match_score = {}
        for catalog_id, catalog_leaves in search_index.items():
            for solution in catalog_leaves:
                group, name, version = solution['solution_group'], solution["solution_name"], solution["solution_version"]

                unique_id = "_".join([catalog_id, group, name, version])

                # todo: nice searching algorithm here
                for keyword in keywords:
                    solution_result = keyword in solution["description"]
                    if solution_result:
                        if unique_id in match_score.keys():
                            match_score[unique_id] = match_score[unique_id] + 1
                        else:
                            match_score[unique_id] = 1

        sorted_results = sorted(match_score.items(), key=operator.itemgetter(1))
        module_logger().info('Search results for "%s"...' % keywords)
        module_logger().info(sorted_results)

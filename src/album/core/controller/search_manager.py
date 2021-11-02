import operator

from album.core.concept.singleton import Singleton
from album.core.controller.collection.collection_manager import CollectionManager
from album.runner import logging

module_logger = logging.get_active_logger


class SearchManager(metaclass=Singleton):
    """Class responsible for searching with keywords through all configured catalogs. Solutions must not be installed
    to be findable in a search request.


    """

    def __init__(self):
        self.catalog_collection = CollectionManager().catalog_collection

    def search(self, keywords):
        """Function corresponding to the `search` subcommand of `album`.

        Searches through album catalogs to find closest matching solution.

        """
        module_logger().debug("Searching with following arguments %s..." % ", ".join(keywords))

        search_index = self.catalog_collection.get_all_solutions()
        match_score = {}
        for solution_entry in search_index:
            group, name, version = solution_entry['group'], solution_entry["name"], solution_entry["version"]
            catalog_id = solution_entry["catalog_id"]
            unique_id = "_".join([str(catalog_id), group, name, version])

            # todo: nice searching algorithm here
            for keyword in keywords:
                solution_result = keyword in solution_entry["description"]
                if solution_result:
                    if unique_id in match_score.keys():
                        match_score[unique_id] = match_score[unique_id] + 1
                    else:
                        match_score[unique_id] = 1

        sorted_results = sorted(match_score.items(), key=operator.itemgetter(1))
        module_logger().info('Search results for "%s"...' % keywords)
        module_logger().info(sorted_results)
        return sorted_results

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
            catalog_name = CollectionManager().catalogs().get_by_id(catalog_id).name
            unique_id = ":".join([str(catalog_name), group, name, version])

            # todo: nice searching algorithm here
            for keyword in keywords:
                self._find_matches(keyword, match_score, solution_entry, unique_id)

        sorted_results = sorted(match_score.items(), key=operator.itemgetter(1), reverse=True)
        return sorted_results

    def _find_matches(self, keyword, match_score, entry, unique_id):
        if isinstance(entry, str):
            solution_result = keyword in entry
            if solution_result:
                if unique_id in match_score.keys():
                    match_score[unique_id] = match_score[unique_id] + 1
                else:
                    match_score[unique_id] = 1
        if isinstance(entry, dict):
            for name, value in entry.items():
                self._find_matches(keyword, match_score, value, unique_id)
        if isinstance(entry, list):
            for item in entry:
                self._find_matches(keyword, match_score, item, unique_id)

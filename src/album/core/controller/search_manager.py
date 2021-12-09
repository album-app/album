import operator

from album.core.api.album import IAlbum
from album.core.api.controller.search_manager import ISearchManager
from album.runner import album_logging

module_logger = album_logging.get_active_logger


class SearchManager(ISearchManager):

    def __init__(self, album: IAlbum):
        self.collection_manager = album.collection_manager()

    def search(self, keywords):
        module_logger().debug("Searching with following arguments %s..." % ", ".join(keywords))

        search_index = self.collection_manager.get_collection_index().get_all_solutions()
        match_score = {}
        for solution_entry in search_index:
            solution_attrs = solution_entry.setup()
            group, name, version = solution_attrs['group'], solution_attrs["name"], solution_attrs["version"]
            catalog_id = solution_entry.internal()["catalog_id"]
            catalog_name = self.collection_manager.catalogs().get_by_id(catalog_id).name()
            unique_id = ":".join([str(catalog_name), group, name, version])

            # todo: nice searching algorithm here
            for keyword in keywords:
                self._find_matches(keyword, match_score, solution_attrs, unique_id)

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

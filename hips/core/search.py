import operator

from hips.core.model import logging
from hips.core.model.configuration import HipsCatalogConfiguration

module_logger = logging.get_active_logger


def search(args):
    HipsSearcher().search(args.keywords)


class HipsSearcher:
    catalog_configuration = None

    def __init__(self):
        self.catalog_configuration = HipsCatalogConfiguration()

    def search(self, keywords):
        """Function corresponding to the `search` subcommand of `hips`.

        Searches through hips catalogs to find closest matching hips
        """
        module_logger().debug("Searching with following arguments %s..." % ", ".join(keywords))

        search_index = self.catalog_configuration.get_search_index()
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
                            match_score[unique_id] = match_score[unique_id]  + 1
                        else:
                            match_score[unique_id] = 1

        sorted_results = sorted(match_score.items(), key=operator.itemgetter(1))
        module_logger().info('Search results for "%s"...' % keywords)
        module_logger().info(sorted_results)

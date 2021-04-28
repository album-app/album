import argparse
import operator
from functools import reduce

from acora import AcoraBuilder

from hips.core.model import logging
from hips.core.model.resolve import get_search_index

module_logger = logging.get_active_logger


def search(args):
    """Function corresponding to the `search` subcommand of `hips`.

    Searches through hips catalogs to find closest matching hips
    """
    parser = argparse.ArgumentParser(description='HIPS search')
    parser.add_argument('keywords',
                        type=str,
                        nargs='+',
                        help='Search keywords')
    search_args = parser.parse_args()
    module_logger().debug("Searching with following arguments %s..." % ", ".join(search_args.keywords))

    builder = AcoraBuilder()
    builder.update(search_args.keywords)
    searcher = builder.build()

    search_index = get_search_index()
    match_score = {}
    for catalog_id, catalog_leaves in search_index.items():
        for solution in catalog_leaves:
            group, name, version = solution['solution_group'], solution["solution_name"], solution["solution_version"]

            unique_id = "_".join([catalog_id, group, name, version])

            # todo: search in more than only the description!
            # todo: make searching case insensitive, allow searching with errors
            # todo: maybe not use aho-corasick? not good for approximation search
            # todo: can also use the node searching method from "anytree" package, the catalog index is build of.
            solution_result = searcher.findall(solution["description"])
            if solution_result:
                score = reduce(lambda a, b: a + b, [v[1] for v in solution_result])
                match_score[unique_id] = score

    sorted_results = sorted(match_score.items(), key=operator.itemgetter(1))
    module_logger().info('Search results for "%s"...' % search_args.keywords)
    module_logger().info(sorted_results)

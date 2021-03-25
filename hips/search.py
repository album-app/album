import argparse
import operator
import os
import sys
from functools import reduce

import gitdir
import yaml
from acora import AcoraBuilder
from xdg import xdg_cache_home

from utils import hips_logging

module_logger = hips_logging.get_active_logger


# ToDo: use the paths in public API
def hips_cache_home():
    """Return the path for the HIPS cache, e.g. ~/.config/hips/cache"""
    return os.path.join(xdg_cache_home(), 'hips', 'cache')


def load_search_index():
    """Load a package search index. This is a dictionary of package name:dicts."""
    search_cache = os.path.join(hips_cache_home(), 'catalog')
    gitdir.download(
        'https://gitlab.com/ida-mdc/hips-catalog/-/tree/main/catalog',
        output_dir=search_cache)

    search_index = {}
    listing = os.listdir(search_cache)
    for filename in listing:
        yml = yaml.load(os.path.join(search_cache, filename))
        search_index[yml['name']] = yml

    return search_index


def search(args):
    """Function corresponding to the `search` subcommand of `hips`.

    Searches through hips catalog to find closest matching hips
    """
    sys.argv = ['search'] + sys.argv
    parser = argparse.ArgumentParser(description='HIPS search')
    parser.add_argument('keywords',
                        type=str,
                        nargs='+',
                        help='Search keywords')
    search_args = parser.parse_args()

    builder = AcoraBuilder()
    builder.update(search_args.keywords)
    searcher = builder.build()

    search_index = load_search_index()
    match_score = {}
    for package_name, package in search_index.items():
        package_result = searcher.findall(package_name +
                                          package['description'])
        score = reduce(lambda a, b: a + b, [v[1] for v in package_result])
        match_score[package['name']] = score

    sorted_results = sorted(match_score.items(), key=operator.itemgetter(1))
    module_logger().info('Search results for "%s"' % search_args.keywords)
    module_logger().info(sorted_results)

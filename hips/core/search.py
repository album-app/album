from hips.core.controller.search_manager import SearchManager

search_manager = SearchManager()


def search(args):
    search_manager.search(args.keywords)

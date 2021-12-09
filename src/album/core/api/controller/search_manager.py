from abc import ABCMeta, abstractmethod


class ISearchManager:
    """Interface responsible for searching with keywords through all configured catalogs. Solutions must not be installed
    to be findable in a search request.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def search(self, keywords):
        """Function corresponding to the `search` subcommand of `album`.

        Searches through album catalogs to find closest matching solution.

        """
        raise NotImplementedError

"""Interface for search manager class."""
from abc import ABCMeta, abstractmethod
from typing import Any, List, Tuple


class ISearchManager:
    """Interface responsible for searching with keywords through all configured catalogs.

    Solutions must not be installed to be findable in a search request.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def search(self, keywords: List[str]) -> List[Tuple[Any, Any]]:
        """Search subcommand of album.

        Searches through album catalogs to find the closest matching solution.

        """
        raise NotImplementedError

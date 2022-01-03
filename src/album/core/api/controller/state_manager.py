from abc import ABCMeta, abstractmethod
from typing import Optional

from album.runner.core.api.model.solution import ISolution


class IStateManager:
    __metaclass__ = ABCMeta

    @abstractmethod
    def load(self, path) -> Optional[ISolution]:
        raise NotImplementedError

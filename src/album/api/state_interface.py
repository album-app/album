from abc import ABCMeta, abstractmethod
from typing import Optional

from album.runner.model.solution import Solution


class StateInterface:
    __metaclass__ = ABCMeta

    @abstractmethod
    def load(self, path) -> Optional[Solution]:
        raise NotImplementedError

    @abstractmethod
    def pop_active_solution(self):
        raise NotImplementedError

    @abstractmethod
    def get_active_solution(self) -> Optional[Solution]:
        raise NotImplementedError

    @abstractmethod
    def get_parent_solution(self) -> Optional[Solution]:
        raise NotImplementedError

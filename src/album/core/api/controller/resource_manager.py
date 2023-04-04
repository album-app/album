from abc import ABCMeta, abstractmethod
from pathlib import Path

from album.core.api.model.catalog import ICatalog
from album.runner.core.api.model.solution import ISolution


class IResourceManager:

    __metaclass__ = ABCMeta

    """Class handling the build process of solutions, so collecting all deploy important files."""

    @abstractmethod
    def write_solution_files(self, catalog: ICatalog, catalog_local_src: str,
                             active_solution: ISolution, deploy_path: Path):
        raise NotImplementedError

    @abstractmethod
    def write_solution_environment_file(self, solution: ISolution, solution_home: Path):
        raise NotImplementedError

from abc import ABCMeta, abstractmethod

from album.runner.model.coordinates import Coordinates


class TestInterface:
    """Interface managing testing routine of a solution. Similar to the installation process, a configured \"test \"
    routine of a solution is executed in the target environment (The conda environment the solution lives in).
    Solutions must be installed to run their testing routine."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def test(self, path, args=None):
        """Function corresponding to the `test` subcommand of `album`."""
        raise NotImplementedError

    @abstractmethod
    def test_from_catalog_coordinates(self, catalog_name: str, coordinates: Coordinates, argv=None):
        raise NotImplementedError

    @abstractmethod
    def test_from_coordinates(self, coordinates: Coordinates, argv=None):
        raise NotImplementedError


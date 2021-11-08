from album.core.model.catalog import Catalog
from album.core.model.coordinates import Coordinates

from album.core import Solution


class ResolveResult:
    def __init__(self, path, catalog, collection_entry, coordinates, loaded_solution=None):
        self.catalog: Catalog = catalog
        self.path = path
        self.collection_entry: dict = collection_entry
        self.coordinates: Coordinates = coordinates
        self.loaded_solution: Solution = loaded_solution

    def __eq__(self, other):
        return isinstance(other, ResolveResult) and \
               other.catalog == self.catalog and \
               other.path == self.path and \
               other.loaded_solution == self.loaded_solution and \
               other.collection_entry == self.collection_entry and \
               other.coordinates == self.coordinates

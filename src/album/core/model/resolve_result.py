from album.core import Solution
from album.core.model.catalog import Catalog
from album.core.model.collection_index import CollectionIndex
from album.runner.model.coordinates import Coordinates


class ResolveResult:
    def __init__(self, path, catalog: Catalog, collection_entry: CollectionIndex.CollectionSolution, coordinates: Coordinates, loaded_solution=None):
        self.catalog: Catalog = catalog
        self.path = path
        self.collection_entry: CollectionIndex.CollectionSolution = collection_entry
        self.coordinates: Coordinates = coordinates
        self.loaded_solution: Solution = loaded_solution

    def __eq__(self, other):
        return isinstance(other, ResolveResult) and \
               other.catalog == self.catalog and \
               other.path == self.path and \
               other.loaded_solution == self.loaded_solution and \
               other.collection_entry == self.collection_entry and \
               other.coordinates == self.coordinates

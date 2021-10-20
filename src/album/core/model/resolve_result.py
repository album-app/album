from album.core import Solution


class ResolveResult:
    def __init__(self, path, catalog, solution_attrs, coordinates, loaded_solution=None):
        self.catalog = catalog
        self.path = path
        self.solution_attrs: dict = solution_attrs
        self.coordinates = coordinates
        self.loaded_solution: Solution = loaded_solution

    def __eq__(self, other):
        return isinstance(other, ResolveResult) and \
               other.catalog == self.catalog and \
               other.path == self.path and \
               other.loaded_solution == self.loaded_solution and \
               other.solution_attrs == self.solution_attrs and \
               other.coordinates == self.coordinates

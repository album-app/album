from album.core import Solution


class ResolveResult:
    def __init__(self, path=None, catalog=None, active_solution=None, solution_attrs=None, coordinates=None):
        self.catalog = catalog
        self.path = path
        self.loaded_solution: Solution = active_solution
        self.solution_attrs: dict = solution_attrs
        self.coordinates = coordinates

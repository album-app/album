class ResolveResult:
    def __init__(self, path=None, catalog=None, active_solution=None, solution_attrs=None):
        self.catalog = catalog
        self.path = path
        self.active_solution = active_solution
        self.solution_attrs = solution_attrs

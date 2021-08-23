class SolutionCollection:

    # path to the parent dependency script.
    parent_script_path = None

    parent_script_catalog = None

    # The hip solution objects of all steps.
    steps_solution = None

    # The step description of the step. Must hold the argument keyword.
    steps = None

    def __init__(self, parent_script_path=None, parent_script_catalog=None, steps_solution=None, steps=None):
        if steps_solution is None:
            steps_solution = []
        if steps is None:
            steps = []
        self.parent_script_path = parent_script_path
        self.parent_script_catalog = parent_script_catalog
        self.steps_solution = steps_solution
        self.steps = steps
        pass

    def __eq__(self, o: object) -> bool:
        return isinstance(o, SolutionCollection) and \
               o.parent_script_path == self.parent_script_path and \
               o.parent_script_catalog == self.parent_script_catalog and \
               o.steps_solution == self.steps_solution and \
               o.steps == self.steps


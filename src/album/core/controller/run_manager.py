import argparse
from queue import Queue, Empty

from album.core import load
from album.core.concept.singleton import Singleton
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.model.coordinates import Coordinates
from album.core.utils.script import create_solution_script
from album.runner import logging

module_logger = logging.get_active_logger


class SolutionCollection:

    def __init__(
            self,
            parent_parsed_args=None,
            parent_script_path=None,
            parent_script_catalog=None,
            steps_solution=None,
            steps=None
    ):
        if parent_parsed_args is None:
            parent_parsed_args = [None]
        if steps_solution is None:
            steps_solution = []
        if steps is None:
            steps = []
        self.parent_parsed_args = parent_parsed_args
        self.parent_script_path = parent_script_path  # path to the parent dependency script.
        self.parent_script_catalog = parent_script_catalog
        self.steps_solution = steps_solution  # The solution objects of all steps.

        self.steps = steps  # The step description of the step. Must hold the argument keyword.

    def __eq__(self, o: object) -> bool:
        return isinstance(o, SolutionCollection) and \
               o.parent_script_path == self.parent_script_path and \
               o.parent_script_catalog == self.parent_script_catalog and \
               o.steps_solution == self.steps_solution and \
               o.steps == self.steps


class RunManager(metaclass=Singleton):
    """Class managing the running process of a solution.

    A solution is executed in its target environment which is created during installation. This class performs all
    operations necessary to run a solution. Resolving of a solution in all configured catalogs,
    dependency checking, and more.

     Attributes:
         collection_manager:
            Holding all configured catalogs. Resolves inside our outside catalogs.

    """
    # singletons
    collection_manager = None

    def __init__(self):
        self.collection_manager = CollectionManager()
        self.init_script = ""

    def run(self, path, run_immediately=False, argv=None):
        """Function corresponding to the `run` subcommand of `album`."""

        resolve_result = self.collection_manager.resolve_require_installation_and_load(path)

        resolve_result.active_solution.set_cache_paths(catalog_name=resolve_result.catalog.name)
        if not resolve_result.active_solution.parent:
            resolve_result.active_solution.set_environment(resolve_result.catalog.name)

        if not resolve_result.catalog:
            module_logger().debug('album loaded locally: %s...' % str(resolve_result.active_solution))
        else:
            module_logger().debug('album loaded from catalog: \"%s\"...' % str(resolve_result.active_solution))

        self._run(resolve_result.active_solution, run_immediately, argv)

    def run_from_catalog_coordinates(self, catalog_name: str, coordinates: Coordinates, run_immediately=False, argv=None):
        catalog = self.collection_manager.catalogs().get_by_name(catalog_name)
        resolve_result = self.collection_manager.resolve_download_and_load_catalog_coordinates(catalog, coordinates)
        self._run(resolve_result.active_solution, run_immediately, argv)

    def run_from_coordinates(self, coordinates: Coordinates, run_immediately=False, argv=None):
        resolve_result = self.collection_manager.resolve_download_and_load_coordinates(coordinates)
        self._run(resolve_result.active_solution, run_immediately, argv)

    def _run(self, active_solution, run_immediately=False, argv=None):
        """Run an already loaded solution which consists of multiple steps (= other solution)."""
        module_logger().info("Starting running \"%s\"" % active_solution["name"])

        if argv is None:
            argv = [""]

        # pushing album and their scripts to a queue
        que = Queue()

        # builds the queue
        self.build_queue(active_solution, que, run_immediately, argv)

        # runs the queue
        self.run_queue(que)

        module_logger().info("Finished running \"%s\"" % active_solution["name"])

    def run_queue(self, que):
        """Runs the que. Queue consists of "solution_object and their scripts"-entries. Order matters!

        Args:
            que:
                The queue object holding entries of solution_object and their scripts

        """
        module_logger().debug("Running queue...")
        try:
            while True:
                solution_object, scripts = que.get(block=False)
                module_logger().info("Running task \"%s\"..." % solution_object["name"])

                self._run_in_environment_with_own_logger(solution_object, scripts)
                module_logger().info("Finished running task \"%s\"!" % solution_object["name"])
                que.task_done()
        except Empty:
            module_logger().info("Currently nothing more to run!")

    def build_queue(self, active_solution, que, run_immediately=False, argv=None):
        """Builds the queue of an active-album object.

        Args:
            active_solution:
                The active_solution object to build the run-que for.
            que:
                The que object.
            run_immediately:
                Boolean. When true, a collection is run immediately without solving for further steps and pushing them
                to the queue. Can result in resolving problems in further downstream collections. Necessary for
                branching decisions.
            argv:
                The argument vector being passed to the solution.

        """
        if argv is None:
            argv = [""]
        steps = active_solution["steps"]
        if steps:  # solution consists of at least one step
            # a step base album is first initialized in the album environment to be able to harvest it's arguments
            # active_solution.init() THIS FEATURE IS TEMPORARY DISABLED

            step_solution_parsed_args = self.__parse_args(active_solution, argv)
            module_logger().info("Building queue for %s steps.." % len(steps))

            for i, step in enumerate(steps):
                module_logger().debug("Adding step %s / %s to queue..." % (i, len(steps)))
                if type(step) is list:
                    self.build_steps_queue(que, step, run_immediately, step_solution_parsed_args)
                else:
                    self.build_steps_queue(que, [step], run_immediately, step_solution_parsed_args)
        else:  # single element queue, no steps
            if active_solution.parent:
                module_logger().debug("Adding step standalone album with parent to queue...")
                # create script with parent
                que.put(self.create_solution_run_with_parent_script_standalone(active_solution, argv))
            else:
                module_logger().debug("Adding step standalone to queue...")
                # create script without parent
                que.put(self.create_solution_run_script_standalone(active_solution, argv))

    def build_steps_queue(self, que, steps, run_immediately=False, step_solution_parsed_args=None):
        """Builds the queue of step-album to be executed. FIFO queue expected.

        Args:
            step_solution_parsed_args:
                Namespace object from parsing the step-solution arguments
            que:
                The queue object.
            steps:
                The steps of a stepped-hip solution.
            run_immediately:
                Boolean. When true, a collection is run immediately without solving for further steps and pushing them
                to the queue. Can result in resolving problems in further downstream collections. Necessary for
                branching decisions.

        """
        # start with an empty collection of steps with the same parent
        same_parent_step_collection = SolutionCollection(step_solution_parsed_args)

        for step in steps:
            module_logger().debug('resolving step \"%s\"...' % step["name"])
            resolve_result = self.collection_manager.resolve_dependency_require_installation_and_load(step)
            active_solution = resolve_result.active_solution

            if active_solution.parent:  # collect steps as long as they have the same parent
                current_parent_script_resolve = self.collection_manager.resolve_dependency_require_installation(
                    active_solution.parent)
                current_parent_script_path = current_parent_script_resolve.path
                current_parent_script_catalog = current_parent_script_resolve.catalog

                # check whether the step has the same parent as the previous steps
                if same_parent_step_collection.parent_script_path and \
                        same_parent_step_collection.parent_script_path != current_parent_script_path:

                    # put old collection to queue
                    que.put(self.create_solution_run_collection_script(same_parent_step_collection))

                    # runs the old collection immediately
                    if run_immediately:
                        self.run_queue(que)

                    # set new parent
                    same_parent_step_collection.parent_script_path = current_parent_script_path
                    same_parent_step_collection.parent_script_catalog = current_parent_script_catalog

                    # overwrite old steps
                    same_parent_step_collection.steps_solution = [active_solution]
                    same_parent_step_collection.steps = [step]

                else:  # same or new parent
                    module_logger().debug('Pushed step \"%s\" in queue...' % step["name"])

                    # set parent
                    same_parent_step_collection.parent_script_path = current_parent_script_path
                    same_parent_step_collection.parent_script_catalog = current_parent_script_catalog

                    # append another step to the steps already having the same parent
                    same_parent_step_collection.steps_solution.append(active_solution)
                    same_parent_step_collection.steps.append(step)

            else:  # add a step without collection (also parent)
                # put collection (if any) to queue
                if same_parent_step_collection.parent_script_path:
                    que.put(self.create_solution_run_collection_script(same_parent_step_collection))

                # empty the collection for possible next steps
                same_parent_step_collection = SolutionCollection(step_solution_parsed_args)

                # run the old collection immediately
                if run_immediately:
                    self.run_queue(que)

                # harvest arguments in the description of the step
                step_args = self._get_args(step, step_solution_parsed_args[0])

                # add step without parent
                active_solution.set_cache_paths(resolve_result.catalog.name)
                active_solution.set_environment(resolve_result.catalog.name)
                que.put(self.create_solution_run_script_standalone(active_solution, step_args))

        # put rest to queue
        if same_parent_step_collection.parent_script_path:
            que.put(self.create_solution_run_collection_script(same_parent_step_collection))

        # run the old collection immediately
        if run_immediately:
            self.run_queue(que)

    def create_solution_run_script_standalone(self, active_solution, args):
        """Creates the execution script for a album object giving its arguments.

        Args:
            active_solution:
                The hip solution object to create the executable script for.
            args:
                The arguments integrated in the script.

        Returns:
                The hip solution object and its scripts (in a list)

        """
        module_logger().debug('Creating standalone album script \"%s\"...' % active_solution["name"])
        script_inset = self.init_script
        if active_solution['run'] and callable(active_solution['run']):
            script_inset += "\nget_active_solution().run()\n"
        else:
            raise ValueError("No \"run\" routine specified for solution \"%s\"! Aborting..." % active_solution["name"])
        if active_solution['close'] and callable(active_solution['close']):
            script_inset += "\nget_active_solution().close()\n"
        script = create_solution_script(active_solution, script_inset, args)

        return [active_solution, [script]]

    def create_solution_run_with_parent_script_standalone(self, active_solution, args):
        """Creates the execution script for a album object having a parent dependency giving its arguments.

        Args:
            active_solution:
                The hip solution object to create the executable script for.
            args:
                The arguments integrated in the script.

        Returns:
                The hip solution object and its scripts (in a list).

        """
        module_logger().debug('Creating album script with parent \"%s\"...' % active_solution.parent["name"])
        parent_solution_resolve = self.collection_manager.resolve_dependency_require_installation_and_load(
            active_solution.parent)
        parent_solution_resolve.active_solution.set_cache_paths(parent_solution_resolve.catalog.name)
        parent_solution_resolve.active_solution.set_environment(parent_solution_resolve.catalog.name)

        # handle arguments
        parent_args, active_solution_args = self.resolve_args(
            parent_solution=parent_solution_resolve.active_solution,
            steps_solution=[active_solution],
            steps=[None],
            step_solution_parsed_args=[None],
            args=args
        )

        # create script
        scripts = self.create_solution_run_with_parent_script(
            parent_solution_resolve.active_solution, parent_args, [active_solution], active_solution_args
        )

        return [parent_solution_resolve.active_solution, scripts]

    def create_solution_run_collection_script(self, solution_collection: SolutionCollection):
        """Creates the execution script for a collection of hip solutions all having the same parent dependency.

        Args:
            solution_collection
        Returns:
            The hip solution shared parent object and its scripts.

        """
        # load parent & steps
        parent_solution = load(solution_collection.parent_script_path)
        parent_solution.set_cache_paths(catalog_name=solution_collection.parent_script_catalog.name)
        parent_solution.set_environment(solution_collection.parent_script_catalog.name)
        module_logger().debug('Creating script for steps (%s) with parent \"%s\"...' % (
            ", ".join([s["name"] for s in solution_collection.steps_solution]), parent_solution["name"]))

        # handle arguments
        parsed_parent_args, parsed_steps_args_list = self.resolve_args(
            parent_solution=parent_solution,
            steps_solution=solution_collection.steps_solution,
            steps=solution_collection.steps,
            step_solution_parsed_args=solution_collection.parent_parsed_args,
        )

        # create script
        scripts = self.create_solution_run_with_parent_script(parent_solution, parsed_parent_args,
                                                              solution_collection.steps_solution,
                                                              parsed_steps_args_list)

        return [parent_solution, scripts]

    def create_solution_run_with_parent_script(self, parent_solution, parent_args, child_solution_list, child_args):
        """Creates the script for the parent hip solution as well as for all its steps (child solutions).

        Args:
            parent_solution:
                The parent solution object.
            parent_args:
                Arguments to use for the parent call.
            child_solution_list:
                A list of all solution objects to be executed with the same parent.
            child_args:
                List of arguments for the call of each child solution.

        Returns:
            A list holding all execution scripts.

        """
        script_parent = create_solution_script(parent_solution,
                                               self.init_script + "\nget_active_solution().run()\n",
                                               parent_args)
        script_list = [script_parent]
        for child_solution, child_args in zip(child_solution_list, child_args):
            child_solution.environment = parent_solution.environment
            child_script = "\nmodule_logger().info(\"Started %s\")\n" % child_solution["name"]
            child_script += "\nget_active_solution().run()\n"
            if hasattr(child_solution, "close"):
                child_script += "\nget_active_solution().close()\n"
            child_script += "\nmodule_logger().info(\"Finished %s\")\n" % child_solution["name"]
            child_script += "\npop_active_solution()\n"
            script_list.append(create_solution_script(child_solution, child_script, child_args))

        script_parent_close = "\nget_active_solution().close()\n" if hasattr(parent_solution, "close") else ""
        script_parent_close += "\npop_active_solution()\n"
        script_list.append(script_parent_close)
        return script_list

    def __parse_args(self, active_solution, args):
        """Parse arguments of loaded solution."""
        parser = argparse.ArgumentParser()

        class FileAction(argparse.Action):
            def __init__(self, option_strings, dest, nargs=None, **kwargs):
                if nargs is not None:
                    raise ValueError("nargs not allowed")
                super(FileAction, self).__init__(option_strings, dest, **kwargs)

            def __call__(self, parser, namespace, values, option_string=None):
                setattr(namespace, self.dest, active_solution.get_arg(self.dest)['action'](values))

        for element in active_solution["args"]:
            if 'action' in element.keys():
                parser.add_argument("--" + element["name"], action=FileAction)
            else:
                parser.add_argument("--" + element["name"])

        return parser.parse_known_args(args=args)

    def resolve_args(self, parent_solution, steps_solution, steps, step_solution_parsed_args, args=None):
        """Resolves arguments of all steps and their parents."""
        args = [] if args is None else args
        parsed_parent_args = None
        parsed_steps_args_list = []

        module_logger().debug('Parsing arguments...')

        # iterate over all steps and parse arguments together
        for idx, step_solution in enumerate(steps_solution):
            step_parser = argparse.ArgumentParser()

            # the steps description
            step = steps[idx]

            if step:  # case steps argument resolving
                step_args = self._get_args(step, step_solution_parsed_args[0])
            else:  # case single step solution
                step_args = args

            # add parent arguments to the step album object arguments
            if 'args' in step_solution["parent"]:
                for param in step_solution["parent"]["args"]:
                    step_args.insert(0, f"--{param['name']}={str(param['value'])}")

            # add parent arguments
            [step_parser.add_argument("--" + element["name"]) for element in parent_solution["args"]]

            # parse all known arguments
            args_known, args_unknown = step_parser.parse_known_args(step_args)

            # only set parents args if not already set
            if not parsed_parent_args:
                parsed_parent_args = [""]
                parsed_parent_args.extend(
                    ["--" + arg_name + "=" + getattr(args_known, arg_name) for arg_name in vars(args_known)])
                module_logger().debug(
                    'For step \"%s\" set parent arguments to %s...' % (step_solution["name"], parsed_parent_args)
                )

            # args_unknown are step args
            parsed_steps_args_list.append(args_unknown)
            module_logger().debug('For step \"%s\" set step arguments to %s...' % (step_solution["name"], args_unknown))

        return parsed_parent_args, parsed_steps_args_list

    @staticmethod
    def _run_in_environment_with_own_logger(active_solution, scripts):
        """Pushes a new logger to the stack before running the solution and pops it afterwards."""
        logging.configure_logging(active_solution['name'])
        module_logger().info("Starting solution \"%s\"..." % active_solution['name'])
        module_logger().info("Citation information: %s" % active_solution['cite'])
        active_solution.environment.run_scripts(scripts)
        logging.pop_active_logger()

    @staticmethod
    def _get_args(step, args):
        """Parse callable arguments belonging to a step into a list of strings"""
        argv = [""]
        if 'args' in step:
            for param in step["args"]:
                argv.append(f"--{param['name']}={str(param['value'](args))}")
        return argv
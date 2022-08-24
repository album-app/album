import argparse
from queue import Queue, Empty
from typing import List

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.script_manager import IScriptManager
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.controller.run_manager import SolutionGroup
from album.core.model.script_queue_entry import ScriptQueueEntry
from album.core.utils.operations.resolve_operations import build_resolve_string
from album.core.utils.operations.solution_operations import (
    get_steps_dict,
    get_parent_dict,
)
from album.runner.album_logging import get_active_logger
from album.runner.core.api.model.script_creator import IScriptCreator
from album.runner.core.api.model.solution import ISolution
from album.runner.core.model.script_creator import (
    ScriptCreatorRun,
    ScriptCreatorRunWithParent,
)

module_logger = get_active_logger


class ScriptManager(IScriptManager):
    def __init__(self, album: IAlbumController):
        self.album = album

    def run_solution_script(
        self, resolve_result: ICollectionSolution, script_creator: ScriptCreatorRun
    ):
        queue = Queue()
        self.build_queue(resolve_result, queue, script_creator, False, [""])
        script_queue_entry = queue.get(block=False)
        self.album.environment_manager().run_scripts(
            script_queue_entry.environment,
            script_queue_entry.scripts,
            pipe_output=False,
        )

    def run_queue(self, queue: Queue):
        module_logger().debug("Running queue...")
        try:
            while True:
                script_queue_entry = queue.get(block=False)
                module_logger().debug(
                    'Running task "%s"...' % script_queue_entry.coordinates.name()
                )
                self._run_in_environment(script_queue_entry)
                module_logger().debug(
                    'Finished running task "%s"!'
                    % script_queue_entry.coordinates.name()
                )
                queue.task_done()
        except Empty:
            module_logger().debug("Currently nothing more to run!")

    def build_queue(
        self,
        collection_solution: ICollectionSolution,
        queue,
        script_creator: ScriptCreatorRun,
        run_immediately=False,
        argv=None,
    ):
        if argv is None:
            argv = [""]
        solution = collection_solution.loaded_solution()
        steps = get_steps_dict(solution)
        if steps:  # solution consists of at least one step
            # a step base album is first initialized in the album environment to be able to harvest it's arguments
            # active_solution.init() THIS FEATURE IS TEMPORARY DISABLED

            step_solution_parsed_args = self.__parse_args(solution, argv)
            module_logger().debug("Building queue for %s steps.." % len(steps))

            for i, step in enumerate(steps):
                module_logger().debug(
                    "Adding step %s / %s to queue..." % (i, len(steps))
                )
                if type(step) is list:
                    self._build_steps_queue(
                        queue,
                        step,
                        script_creator,
                        run_immediately,
                        step_solution_parsed_args,
                    )
                else:
                    self._build_steps_queue(
                        queue,
                        [step],
                        script_creator,
                        run_immediately,
                        step_solution_parsed_args,
                    )
        else:  # single element queue, no steps
            parent = get_parent_dict(solution)
            if parent:
                module_logger().debug(
                    "Adding standalone solution with parent to queue..."
                )
                # create script with parent
                queue.put(
                    self._create_solution_run_with_parent_script_standalone(
                        collection_solution, argv, script_creator
                    )
                )
            else:
                module_logger().debug("Adding standalone to queue...")
                # create script without parent
                queue.put(
                    self._create_solution_run_script_standalone(
                        collection_solution, argv, script_creator
                    )
                )

    def _build_steps_queue(
        self,
        queue: Queue,
        steps: list,
        script_creator: ScriptCreatorRun,
        run_immediately=False,
        step_solution_parsed_args=None,
    ):
        """Builds the queue of step-album to be executed. FIFO queue expected.

        Args:
            script_creator:
                The ScriptCreatorRun object to use to create the execution script.
            step_solution_parsed_args:
                Namespace object from parsing the step-solution arguments
            queue:
                The queue object.
            steps:
                The steps of a stepped solution.
            run_immediately:
                Boolean. When true, a collection is run immediately without solving for further steps and pushing them
                to the queue. Can result in resolving problems in further downstream collections. Necessary for
                branching decisions.

        """
        # start with an empty collection of steps with the same parent
        same_parent_step_collection = SolutionGroup(step_solution_parsed_args)
        citations = []

        for step in steps:
            module_logger().debug('resolving step "%s"...' % step["name"])
            resolve_result = self.album.collection_manager().resolve_installed_and_load(
                build_resolve_string(step)
            )

            citations.append(resolve_result.loaded_solution())

            parent = get_parent_dict(resolve_result.loaded_solution())
            if parent:  # collect steps as long as they have the same parent
                current_parent_script_resolve = (
                    self.album.collection_manager().resolve_installed_and_load(
                        build_resolve_string(parent)
                    )
                )

                # check whether the step has the same parent as the previous steps
                if (
                    same_parent_step_collection.parent
                    and same_parent_step_collection.parent.coordinates()
                    != current_parent_script_resolve.coordinates()
                ):

                    # put old collection to queue
                    queue.put(
                        self._create_solution_run_collection_script(
                            same_parent_step_collection, script_creator
                        )
                    )

                    # runs the old collection immediately
                    if run_immediately:
                        self.run_queue(queue)

                    # set new parent
                    same_parent_step_collection.parent = current_parent_script_resolve

                    # overwrite old steps
                    same_parent_step_collection.steps_solution = [
                        resolve_result.loaded_solution()
                    ]
                    same_parent_step_collection.steps = [step]

                else:  # same or new parent
                    module_logger().debug('Pushed step "%s" in queue...' % step["name"])

                    # set parent
                    same_parent_step_collection.parent = current_parent_script_resolve

                    # append another step to the steps already having the same parent
                    same_parent_step_collection.steps_solution.append(
                        resolve_result.loaded_solution()
                    )
                    same_parent_step_collection.steps.append(step)

            else:  # add a step without collection (also parent)
                # put collection (if any) to queue
                if same_parent_step_collection.parent:
                    queue.put(
                        self._create_solution_run_collection_script(
                            same_parent_step_collection, script_creator
                        )
                    )

                # empty the collection for possible next steps
                same_parent_step_collection = SolutionGroup(step_solution_parsed_args)

                # run the old collection immediately
                if run_immediately:
                    self.run_queue(queue)

                # harvest arguments in the description of the step
                step_args = self._get_args(step, step_solution_parsed_args[0])

                # add step without parent
                queue.put(
                    self._create_solution_run_script_standalone(
                        resolve_result, step_args, script_creator
                    )
                )

        # put rest to queue
        if same_parent_step_collection.parent:
            queue.put(
                self._create_solution_run_collection_script(
                    same_parent_step_collection, script_creator
                )
            )

        self._print_credit(citations)

        # run the old collection immediately
        if run_immediately:
            self.run_queue(queue)

    def _create_solution_run_script_standalone(
        self,
        collection_solution: ICollectionSolution,
        args: list,
        script_creator: IScriptCreator,
    ) -> ScriptQueueEntry:
        """Creates the execution script for a album object giving its arguments.

        Args:
            script_creator:
                The ScriptCreator object to use to create the execution script.
            collection_solution:
                The collection solution object to create the executable script for.
            args:
                The arguments integrated in the script.

        Returns:
                The solution object and its scripts (in a list)

        """
        module_logger().debug(
            'Creating standalone album script "%s"...'
            % collection_solution.coordinates().name()
        )

        self._print_credit([collection_solution.loaded_solution()])
        environment = self.album.environment_manager().set_environment(
            collection_solution
        )
        script = script_creator.create_script(
            collection_solution.loaded_solution(), args
        )

        return ScriptQueueEntry(
            collection_solution.coordinates(), [script], environment=environment
        )

    def _create_solution_run_with_parent_script_standalone(
        self,
        collection_solution: ICollectionSolution,
        args: list,
        script_creator: ScriptCreatorRun,
    ) -> ScriptQueueEntry:
        """Creates the execution script for a album object having a parent dependency giving its arguments.

        Args:
            script_creator:
                The ScriptCreatorRun object to use to create the execution script.
            collection_solution:
                The collection solution object to create the executable script for.
            args:
                The arguments integrated in the script.

        Returns:
                The solution object and its scripts (in a list).

        """
        environment = self.album.environment_manager().set_environment(
            collection_solution
        )
        active_solution = collection_solution.loaded_solution()

        # create script
        script = script_creator.create_script(
            collection_solution.loaded_solution(), args
        )

        # TODO this should probably move into the runner
        self._print_credit([active_solution])

        return ScriptQueueEntry(
            collection_solution.loaded_solution().coordinates(), [script], environment
        )

    def _create_solution_run_collection_script(
        self, solution_collection: SolutionGroup, script_creator: ScriptCreatorRun
    ) -> ScriptQueueEntry:
        """Creates the execution script for a collection of solutions all having the same parent dependency.

        Args:
            script_creator:
                The ScriptCreator object to use to create the execution script.
            solution_collection
        Returns:
            The solution shared parent object and its scripts.

        """
        # load parent & steps
        parent_solution = self.album.state_manager().load(
            solution_collection.parent.path()
        )
        self.album.solutions().set_cache_paths(
            parent_solution, solution_collection.parent.catalog()
        )

        environment = self.album.environment_manager().set_environment(
            solution_collection.parent
        )
        module_logger().debug(
            'Creating script for steps (%s) with parent "%s"...'
            % (
                ", ".join(
                    [s.coordinates().name() for s in solution_collection.steps_solution]
                ),
                parent_solution.coordinates().name(),
            )
        )

        # handle arguments
        parsed_parent_args, parsed_steps_args_list = self._resolve_args(
            parent_solution=parent_solution,
            steps_solution=solution_collection.steps_solution,
            steps=solution_collection.steps,
            step_solution_parsed_args=solution_collection.parent_parsed_args,
        )

        # create script
        scripts = self._create_solution_run_with_parent_script(
            parent_solution,
            parsed_parent_args,
            solution_collection.steps_solution,
            parsed_steps_args_list,
            script_creator,
        )

        return ScriptQueueEntry(parent_solution.coordinates(), scripts, environment)

    @staticmethod
    def _create_solution_run_with_parent_script(
        parent_solution: ISolution,
        parent_args: list,
        child_solution_list: List[ISolution],
        child_args: list,
        script_creator: ScriptCreatorRun,
    ):
        """Creates the script for the parent solution as well as for all its steps (child solutions).

        Args:
            script_creator:
                The ScriptCreatorRun object to use to create the execution script.
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
        module_logger().debug(
            'Creating album script with parent "%s"...'
            % parent_solution.coordinates().name()
        )

        script_creator_run_with_parent = ScriptCreatorRunWithParent(
            script_creator, child_solution_list, child_args
        )
        script = script_creator_run_with_parent.create_script(
            parent_solution, parent_args
        )
        script_list = [script]

        return script_list

    def __parse_args(self, active_solution: ISolution, args: list):
        """Parse arguments of loaded solution."""
        parser = argparse.ArgumentParser()

        class FileAction(argparse.Action):
            def __init__(self, option_strings, dest, nargs=None, **kwargs):
                if nargs is not None:
                    raise ValueError("nargs not allowed")
                super(FileAction, self).__init__(option_strings, dest, **kwargs)

            def __call__(self, p, namespace, values, option_string=None):
                setattr(
                    namespace,
                    self.dest,
                    active_solution.get_arg(self.dest)["action"](values),
                )

        for element in active_solution.setup()["args"]:
            if "action" in element.keys():
                parser.add_argument("--" + element["name"], action=FileAction)
            else:
                parser.add_argument("--" + element["name"])

        return parser.parse_known_args(args=args)

    def _resolve_args(
        self,
        parent_solution: ISolution,
        steps_solution: List[ISolution],
        steps: list,
        step_solution_parsed_args: list,
        args=None,
    ):
        """Resolves arguments of all steps and their parents."""
        args = [] if args is None else args
        parsed_parent_args = None
        parsed_steps_args_list = []

        module_logger().debug("Parsing arguments...")

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
            parent_dict = get_parent_dict(step_solution)
            if "args" in parent_dict:
                for param in parent_dict["args"]:
                    step_args.insert(0, f"--{param['name']}={str(param['value'])}")

            # add parent arguments
            if "args" in parent_solution.setup():
                [
                    step_parser.add_argument("--" + element["name"])
                    for element in parent_solution.setup()["args"]
                ]

            # parse all known arguments
            args_known, args_unknown = step_parser.parse_known_args(step_args)

            # only set parents args if not already set
            if not parsed_parent_args:
                parsed_parent_args = [""]
                parsed_parent_args.extend(
                    [
                        "--" + arg_name + "=" + getattr(args_known, arg_name)
                        for arg_name in vars(args_known)
                    ]
                )
                module_logger().debug(
                    'For step "%s" set parent arguments to %s...'
                    % (step_solution.coordinates().name(), parsed_parent_args)
                )

            # args_unknown are step args
            parsed_steps_args_list.append(args_unknown)
            module_logger().debug(
                'For step "%s" set step arguments to %s...'
                % (step_solution.coordinates().name(), args_unknown)
            )

        return parsed_parent_args, parsed_steps_args_list

    def _run_in_environment(self, script_queue_entry: ScriptQueueEntry):
        """Pushes a new logger to the stack before running the solution and pops it afterwards."""
        module_logger().debug(
            'Running script in environment of solution "%s"...'
            % script_queue_entry.coordinates.name()
        )
        self.album.environment_manager().run_scripts(
            script_queue_entry.environment, script_queue_entry.scripts
        )
        module_logger().debug(
            'Done running script in environment of solution "%s"...'
            % script_queue_entry.coordinates.name()
        )

    @staticmethod
    def _get_args(step, args):
        """Parse callable arguments belonging to a step into a list of strings"""
        argv = [""]
        if "args" in step:
            for param in step["args"]:
                argv.append(f"--{param['name']}={str(param['value'](args))}")
        return argv

    @staticmethod
    def _print_credit(active_solutions: List[ISolution]) -> None:
        res = ScriptManager._get_credit_as_string(active_solutions)
        if res:
            module_logger().info(res)

    @staticmethod
    def _get_credit_as_string(active_solutions: List[ISolution]):
        res = ""
        for active_solution in active_solutions:
            if active_solution.setup().cite:
                for citation in active_solution.setup().cite:
                    text = citation["text"]
                    if "doi" in citation:
                        text += " (DOI: %s)" % citation["doi"]
                    res += "%s\n" % text
        if len(res) > 0:
            return "\n\nSolution credits:\n\n%s\n" % res
        return None

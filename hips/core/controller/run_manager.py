import argparse
import sys
from queue import Queue, Empty

from hips.core import load
from hips.core.concept.singleton import Singleton
from hips.core.model.catalog_collection import HipsCatalogCollection
from hips.core.utils.script import create_script
from hips_runner import logging
from hips_runner.logging import LogLevel

module_logger = logging.get_active_logger


class RunManager(metaclass=Singleton):
    """Class managing the running process of a solution.

    A solution is executed in its target environment created during installation. This class performs all operations
    necessary to run a solution. Resolving of a solution in all configured catalogs, dependency checking, and more.

     Attributes:
         catalog_collection:
            Holds all the catalogs of the HIPS framework installation.

    """
    # singletons
    catalog_collection = None

    def __init__(self, catalog_collection=None):
        self.catalog_collection = HipsCatalogCollection() if not catalog_collection else catalog_collection
        self.init_script = ""

    def run(self, path, run_immediately=False):
        """Function corresponding to the `run` subcommand of `hips`."""
        resolve = self.catalog_collection.resolve_from_str(path, download=False)

        if not resolve["catalog"]:
            if not (resolve['path'].is_file() and resolve['path'].stat().st_size > 0):
                raise RuntimeError("Please install solution first!")

        active_hips = load(resolve["path"])

        if not resolve["catalog"]:
            module_logger().debug('hips loaded locally: %s...' % str(active_hips))
        else:
            module_logger().debug('hips loaded from catalog: %s...' % str(active_hips))

        self._run(active_hips, run_immediately)

    def _run(self, active_hips, run_immediately=False):
        """Run an already loaded HIPS which consists of multiple steps (= other HIPS)."""
        module_logger().info("Starting running \"%s\"" % active_hips["name"])

        # pushing hips and their scripts to a queue
        que = Queue()

        # builds the queue
        self.build_queue(active_hips, que, run_immediately)

        # run queue
        self.run_queue(que)

        module_logger().info("Finished running \"%s\"" % active_hips["name"])

    def run_queue(self, que):
        """Runs the que. Queue consists of "hips_object and their scripts"-entries. Order matters!

        Args:
            que:
                The queue object holding entries of hips_object and their scripts

        """
        module_logger().debug("Running queue...")
        try:
            while True:
                hips_object, scripts = que.get(block=False)
                module_logger().info("Running task %s..." % hips_object["name"])

                self._run_in_environment_with_own_logger(hips_object, scripts)
                module_logger().info("Finished running task %s!" % hips_object["name"])
                que.task_done()
        except Empty:
            module_logger().info("Currently nothing more to run!")

    @staticmethod
    def empty_collection():
        """Returns an empty hips-collection dictionary.

        Returns:
            dictionary consisting of the entries:
                    Parent_script_path: path to the parent dependency script.
                steps_hips:
                    The hip solution objects of all steps.
                steps:
                    The step description of the step. Must holds the argument keyword.

        """
        return {
            "parent_script_path": None,
            "steps_hips": [],
            "steps": []
        }

    def build_queue(self, active_hips, que, run_immediately=False):
        """Builds the queue of an active-hips object.

        Args:
            active_hips:
                The active_hips object to build the run-que for.
            que:
                The que object.
            run_immediately:
                Boolean. When true, a collection is run immediately without solving for further steps and pushing them
                to the queue. Can result in resolving problems in further downstream collections. Necessary for
                branching decisions.

        """
        steps = active_hips["steps"]
        if steps:  # solution consists of at least one step
            # a step base hips is first initialized in the hips environment to be able to harvest it's arguments
            # todo: discuss this!
            active_hips.init()

            self.__parse_args(active_hips)
            module_logger().info("Building queue for %s steps.." % len(steps))

            for i, step in enumerate(steps):
                module_logger().debug("Adding step %s / %s to queue..." % (i, len(steps)))
                if type(step) is list:
                    self.build_steps_queue(que, step, run_immediately)
                else:
                    self.build_steps_queue(que, [step], run_immediately)
        else:  # single element queue, no steps
            if active_hips.parent:
                module_logger().debug("Adding step standalone hips with parent to queue...")
                # create script with parent
                que.put(self.create_hips_run_with_parent_script_standalone(active_hips, sys.argv))
            else:
                module_logger().debug("Adding step standalone to queue...")
                # create script without parent
                que.put(self.create_hips_run_script_standalone(active_hips, sys.argv))

    def build_steps_queue(self, que, steps, run_immediately=False):
        """Builds the queue of step-hips to be executed. FIFO queue expected.

        Args:
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
        same_parent_step_collection = self.empty_collection()

        for step in steps:
            module_logger().debug('resolving step \"%s\"...' % step["name"])
            sub_step_path = self.catalog_collection.resolve_hips_dependency(step, download=False)["path"]
            step_hips = load(sub_step_path)

            if step_hips["parent"]:  # collect steps as long as they have the same parent
                current_parent_script_path = self.catalog_collection.resolve_hips_dependency(
                    step_hips["parent"], download=False
                )["path"]

                # check whether the step has the same parent as the previous steps
                if same_parent_step_collection["parent_script_path"] and \
                        same_parent_step_collection["parent_script_path"] != current_parent_script_path:

                    # put old collection to queue
                    que.put(self.create_hips_run_collection_script(same_parent_step_collection))

                    # runs the old collection immediately
                    if run_immediately:
                        self.run_queue(que)

                    # set new parent
                    same_parent_step_collection["parent_script_path"] = current_parent_script_path

                    # overwrite old steps
                    same_parent_step_collection["steps_hips"] = [step_hips]
                    same_parent_step_collection["steps"] = [step]

                else:  # same or new parent
                    module_logger().debug('Pushed step \"%s\" in queue...' % step["name"])

                    # set parent
                    same_parent_step_collection["parent_script_path"] = current_parent_script_path

                    # append another step to the steps already having the same parent
                    same_parent_step_collection["steps_hips"].append(step_hips)
                    same_parent_step_collection["steps"].append(step)

            else:  # add a step without collection (also parent)
                # put collection (if any) to queue
                if same_parent_step_collection["parent_script_path"]:
                    que.put(self.create_hips_run_collection_script(same_parent_step_collection))

                # empty the collection for possible next steps
                same_parent_step_collection = self.empty_collection()

                # run the old collection immediately
                if run_immediately:
                    self.run_queue(que)

                # harvest arguments in the description of the step
                step_args = self._get_args(step)

                # add step without parent
                que.put(self.create_hips_run_script_standalone(step_hips, step_args))

        # put rest to queue
        if same_parent_step_collection["parent_script_path"]:
            que.put(self.create_hips_run_collection_script(same_parent_step_collection))

        # run the old collection immediately
        if run_immediately:
            self.run_queue(que)

    def create_hips_run_script_standalone(self, active_hips, args):
        """Creates the execution script for a hips object giving its arguments.

        Args:
            active_hips:
                The hip solution object to create the executable script for.
            args:
                The arguments integrated in the script.

        Returns:
                The hip solution object and its scripts (in a list)

        """
        module_logger().debug('Creating standalone hips script \"%s\"...' % active_hips["name"])
        script_inset = self.init_script
        if active_hips['run'] and callable(active_hips['run']):
            script_inset += "\nget_active_hips().run()\n"
        else:
            raise ValueError("No \"run\" routine specified for solution %s! Aborting..." % active_hips["name"])
        if active_hips['close'] and callable(active_hips['close']):
            script_inset += "\nget_active_hips().close()\n"
        script = create_script(active_hips, script_inset, args)

        return [active_hips, [script]]

    def create_hips_run_with_parent_script_standalone(self, active_hips, args):
        """Creates the execution script for a hips object having a parent dependency giving its arguments.

        Args:
            active_hips:
                The hip solution object to create the executable script for.
            args:
                The arguments integrated in the script.

        Returns:
                The hip solution object and its scripts (in a list).

        """
        module_logger().debug('Creating hips script with parent \"%s\"...' % active_hips.parent["name"])
        parent_script = self.catalog_collection.resolve_hips_dependency(
            active_hips.parent, download=False
        )["path"]
        parent_hips = load(parent_script)

        # handle arguments
        parent_args, active_hips_args = self.resolve_args(parent_hips, [active_hips], [None], args)

        # create script
        scripts = self.create_hips_run_with_parent_scrip(parent_hips, parent_args, [active_hips], active_hips_args)

        return [parent_hips, scripts]

    def create_hips_run_collection_script(self, hips_collection):
        """Creates the execution script for a collection of hip solutions all having the same parent dependency.

        Args:
            hips_collection:
                dictionary consisting of the entries:
                    Parent_script_path: path to the parent dependency script.
                steps_hips:
                    The hip solution objects of all steps.
                steps:
                    The step description of the step. Must holds the argument keyword.

        Returns:
            The hip solution shared parent object and its scripts.

        """
        # load parent & steps
        parent_hips = load(hips_collection["parent_script_path"])
        steps_hips = hips_collection["steps_hips"]
        steps = hips_collection["steps"]

        module_logger().debug('Creating script for steps (%s) with parent \"%s\"...' % (
            ", ".join([s["name"] for s in steps_hips]), parent_hips["name"]))

        # handle arguments
        parsed_parent_args, parsed_steps_args_list = self.resolve_args(parent_hips, steps_hips, steps)

        # create script
        scripts = self.create_hips_run_with_parent_scrip(parent_hips, parsed_parent_args, steps_hips,
                                                         parsed_steps_args_list)

        return [parent_hips, scripts]

    def create_hips_run_with_parent_scrip(self, parent_hips, parent_args, child_hips_list, child_args):
        """Creates the script for the parent hip solution as well as for all its steps (chid hip solutions).

        Args:
            parent_hips:
                The parent hip solution object.
            parent_args:
                Arguments to use for the parent call.
            child_hips_list:
                A list of all hip solution objects to be executed with the same parent.
            child_args:
                List of arguments for the call of each child solution.

        Returns:
            A list holding all execution scripts.

        """
        script_parent = create_script(parent_hips,
                                      self.init_script + "\nget_active_hips().run()\n",
                                      parent_args)

        script_list = [script_parent]
        for child_hips, child_args in zip(child_hips_list, child_args):
            child_script = "\nmodule_logger().info(\"Started %s\")\n" % child_hips["name"]
            child_script += "\nget_active_hips().run()\n"
            if hasattr(child_hips, "close"):
                child_script += "\nget_active_hips().close()\n"
            child_script += "\nmodule_logger().info(\"Finished %s\")\n" % child_hips["name"]
            child_script += "\npop_active_hips()\n"
            script_list.append(create_script(child_hips, child_script, child_args))

        script_parent_close = "\nget_active_hips().close()\n" if hasattr(parent_hips, "close") else ""
        script_parent_close += "\npop_active_hips()\n"
        script_list.append(script_parent_close)
        return script_list

    def __parse_args(self, active_hips):
        """Parse arguments of loaded HIPS."""
        parser = argparse.ArgumentParser()

        class FileAction(argparse.Action):
            def __init__(self, option_strings, dest, nargs=None, **kwargs):
                if nargs is not None:
                    raise ValueError("nargs not allowed")
                super(FileAction, self).__init__(option_strings, dest, **kwargs)

            def __call__(self, parser, namespace, values, option_string=None):
                active_hips.get_arg(self.dest)['action'](values)

        for element in active_hips["args"]:
            parser.add_argument("--" + element["name"], action=FileAction)
        parser.parse_known_args(args=sys.argv)

    def resolve_args(self, parent_hips, steps_hips, steps, args=None):
        """Resolves arguments of all steps and their parents."""
        args = [] if args is None else args
        parsed_parent_args = None
        parsed_steps_args_list = []

        module_logger().debug('Parsing arguments...')

        # iterate over all steps and parse arguments together
        for idx, step_hips in enumerate(steps_hips):
            step_parser = argparse.ArgumentParser()

            # the steps description
            step = steps[idx]

            if step:  # case steps argument resolving
                step_args = self._get_args(step)
            else:  # case single step hips
                step_args = args

            # add parent arguments to the step hips object arguments
            if 'args' in step_hips["parent"]:
                for param in step_hips["parent"]["args"]:
                    step_args.insert(0, f"--{param['name']}={str(param['value'])}")

            # add parent arguments
            [step_parser.add_argument("--" + element["name"]) for element in parent_hips["args"]]

            # parse all known arguments
            args_known, args_unknown = step_parser.parse_known_args(step_args)

            # only set parents args if not already set
            if not parsed_parent_args:
                parsed_parent_args = [""]
                parsed_parent_args.extend(
                    ["--" + arg_name + "=" + getattr(args_known, arg_name) for arg_name in vars(args_known)])
                module_logger().debug(
                    'For step \"%s\" set parent arguments to %s...' % (step_hips["name"], parsed_parent_args)
                )

            # args_unknown are step args
            parsed_steps_args_list.append(args_unknown)
            module_logger().debug('For step \"%s\" set step arguments to %s...' % (step_hips["name"], args_unknown))

        return parsed_parent_args, parsed_steps_args_list

    @staticmethod
    def _run_in_environment_with_own_logger(active_hips, scripts):
        """Pushes a new logger to the stack before running the solution and pops it afterwards."""
        logging.configure_logging(
            LogLevel(logging.to_loglevel(logging.get_loglevel_name())), active_hips['name']
        )
        module_logger().info("Starting solution \"%s\"..." % active_hips['name'])
        active_hips.environment.run_scripts(scripts)
        logging.pop_active_logger()

    @staticmethod
    def _get_args(step):
        """Parse callable arguments belonging to a step into a list of strings"""
        argv = [""]
        if 'args' in step:
            for param in step["args"]:
                argv.append(f"--{param['name']}={str(param['value']())}")
        return argv

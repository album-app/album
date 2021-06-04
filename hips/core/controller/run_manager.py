import argparse
import sys

from hips.core import load
from hips.core.model.catalog_configuration import HipsCatalogConfiguration
from hips.core.utils.script import create_script, create_hips_with_parent_script
from hips_runner import logging
from hips_runner.logging import LogLevel

module_logger = logging.get_active_logger


class RunManager:
    init_script = ""
    catalog_configuration = None

    def __init__(self):
        self.catalog_configuration = HipsCatalogConfiguration()

    def run(self, path):
        """Function corresponding to the `run` subcommand of `hips`."""
        resolve = self.catalog_configuration.resolve_from_str(path, download=False)

        if not resolve["catalog"]:
            if not (resolve['path'].is_file() and resolve['path'].stat().st_size > 0):
                # todo: install the solution and continue on success
                raise RuntimeError("Please install solution first!")

        active_hips = load(resolve["path"])

        if not resolve["catalog"]:
            module_logger().debug('hips loaded locally: %s...' % str(active_hips))
        else:
            module_logger().debug('hips loaded from catalog: %s...' % str(active_hips))

        self._run(active_hips)

    def _run(self, active_hips):
        """Run an already loaded HIPS which consists of multiple steps (= other HIPS)."""
        module_logger().info("Starting running \"%s\"" % active_hips["name"])

        # a step base hips is first initialized in the hips environment to be able to harvest it's arguments
        active_hips.init()

        steps = active_hips["steps"]
        if steps:
            self.__parse_args(active_hips)
            module_logger().info("Executing %s steps.." % len(steps))

            # iterate over steps and run them
            for i, step in enumerate(steps):
                module_logger().info("Step progress %s / %s" % (i, len(steps)))
                if type(step) is list:
                    self.run_steps(step)
                else:
                    self.run_steps([step])
            module_logger().info("Step progress %s / %s" % (len(steps), len(steps)))
        else:
            self.run_single_step(active_hips, sys.argv)

        module_logger().info("Finished running \"%s\"" % active_hips["name"])

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

    @staticmethod
    def empty_queue():
        return {
            "parent_script_path": None,
            "steps_hips": [],
            "steps": []
        }

    def run_and_empty_queue(self, q):
        if q["parent_script_path"]:
            self.run_hips_collection(q)
        return self.empty_queue()

    def run_steps(self, steps):
        same_parent_steps = self.empty_queue()
        for step in steps:
            module_logger().debug('resolving step \"%s\"...' % step["name"])
            sub_step_path = self.catalog_configuration.resolve_hips_dependency(step, download=False)["path"]
            step_hips = load(sub_step_path)
            if step_hips["parent"]:  # collect steps as long as they have the same parent, then run them collectively
                current_parent_script_path = self.catalog_configuration.resolve_hips_dependency(
                    step_hips["parent"], download=False
                )["path"]

                if same_parent_steps["parent_script_path"] and \
                        same_parent_steps["parent_script_path"] != current_parent_script_path:
                    self.run_hips_collection(same_parent_steps)
                    # set new parent
                    same_parent_steps["parent_script_path"] = current_parent_script_path
                    # overwrite old steps
                    same_parent_steps["steps_hips"] = [step_hips]
                    same_parent_steps["steps"] = [step]
                else:  # same or new parent
                    module_logger().debug('Pushed step \"%s\" in queue...' % step["name"])
                    # set parent
                    same_parent_steps["parent_script_path"] = current_parent_script_path
                    # append another step to the steps already having the same parent
                    same_parent_steps["steps_hips"].append(step_hips)
                    same_parent_steps["steps"].append(step)
            else:
                # empty the queue first
                same_parent_steps = self.run_and_empty_queue(same_parent_steps)
                # simply run this step
                step_args = self._get_args(step)  # arguments in the description of the step
                self.run_single_step(step_hips, step_args)
        # empty queue if necessary
        self.run_and_empty_queue(same_parent_steps)

    def run_hips_collection(self, same_parent_steps):  # run_same_app_hips
        # load parent & steps
        parent_hips = load(same_parent_steps["parent_script_path"])
        steps_hips = same_parent_steps["steps_hips"]
        steps = same_parent_steps["steps"]

        # info
        module_logger().debug(
            'Running queue (%s) with parent \"%s\"...' % (", ".join(
                [s["name"] for s in steps_hips]), parent_hips["name"]
            )
        )

        # handle arguments
        parsed_parent_args, parsed_steps_args_list = self.resolve_args(parent_hips, steps_hips, steps)

        # create script
        script = create_hips_with_parent_script(parent_hips, parsed_parent_args, steps_hips, parsed_steps_args_list,
                                                self.init_script)
        # now run
        self._run_in_environment_with_own_logger(parent_hips, script)

    def resolve_args(self, parent_hips, steps_hips, steps, args=None):
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

    def run_single_step(self, active_hips, args):
        """Run loaded HIPS with given arguments"""
        if active_hips["parent"]:
            module_logger().debug('Found parent solution \"%s\"...' % active_hips["parent"]["name"])
            parent_script = self.catalog_configuration.resolve_hips_dependency(
                active_hips["parent"], download=False
            )["path"]
            parent_hips = load(parent_script)
            parent_args, active_hips_args = self.resolve_args(parent_hips, [active_hips], [None], args)
            self.run_steps_with_parent(parent_hips, parent_args, [active_hips], active_hips_args)
        else:
            self.run_single_step_standalone(active_hips, args)

    def run_single_step_standalone(self, active_hips, args):
        """Run loaded HIPS with given arguments and no parent HIPS app"""
        module_logger().debug('Running standalone step \"%s\"...' % active_hips["name"])
        script_inset = self.init_script
        script_inset += "\nget_active_hips().run()"
        if hasattr(active_hips, "close"):
            script_inset += "\nget_active_hips().close()\n"
        script = create_script(active_hips, script_inset, args)
        self._run_in_environment_with_own_logger(active_hips, script)

    def run_steps_with_parent(self, parent_hips, parent_args, hips_list, hips_args_list):
        """Run one or multiple loaded HIPS with given arguments depending on a HIPS app"""
        module_logger().debug(
            'Running step(s) (%s) under parent \"%s\"...' % (
                ", ".join([h["name"] for h in hips_list]), parent_hips["name"]
            )
        )
        script = create_hips_with_parent_script(parent_hips, parent_args, hips_list, hips_args_list, self.init_script)
        self._run_in_environment_with_own_logger(parent_hips, script)

    @staticmethod
    def _run_in_environment_with_own_logger(active_hips, script):
        """Pushes a new logger to the stack before running the solution and pops it afterwards."""
        logging.configure_logging(
            LogLevel(logging.to_loglevel(logging.get_loglevel_name())), active_hips['name']
        )
        module_logger().info("Starting solution \"%s\"..." % active_hips['name'])
        active_hips.environment.run_script(script)
        logging.pop_active_logger()

    @staticmethod
    def _get_args(step):
        """Parse callable arguments belonging to a step into a list of strings"""
        argv = [""]
        if 'args' in step:
            for param in step["args"]:
                argv.append(f"--{param['name']}={str(param['value']())}")
        return argv

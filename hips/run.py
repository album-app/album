import argparse
import sys

import hips
from hips_utils import hips_logging
from hips_utils.environment import set_environment_path, set_environment_name, run_in_environment
from hips_utils.hips_logging import LogLevel
from hips_utils.hips_resolve import resolve_hips, resolve_from_str
from hips_utils.hips_script import create_script, create_hips_with_parent_script

# ToDo: environment purge method
# ToDo: reusable versioned environments?
# ToDo: test for windows
# ToDo: subprocess logging (https://www.endpoint.com/blog/2015/01/28/getting-realtime-output-using-python)
# ToDo: solutions should not run in hips.yml for comp. reasons. Maybe check that?
# ToDo: install helper - methods (pip install) (git-download) (java-dependcies)


module_logger = hips_logging.get_active_logger


def run(args):
    HIPSRunner().run(args)


class HIPSRunner:

    init_script = ""

    def run(self, args):
        """Function corresponding to the `run` subcommand of `hips`."""
        resolve = resolve_from_str(args.path)

        if not self.__is_in_catalog(resolve["catalog"]):
            # todo: install the solution and continue on success
            raise RuntimeError("Please install solution first!")

        active_hips = hips.load_and_push_hips(resolve["path"])

        if not resolve["catalog"]:
            module_logger().debug('hips loaded locally: %s' % str(active_hips))
        else:
            module_logger().debug('hips loaded from catalog: %s' % str(active_hips))

        if hasattr(active_hips, "steps"):
            self.__run_steps(active_hips)
        else:
            self.__run_single_step(active_hips, sys.argv)

    def __run_steps(self, active_hips):
        """Run an already loaded HIPS which consists of multiple steps (= other HIPS)."""
        # a step base hips is first initialized in the hips environment to be able to harvest it's arguments
        active_hips.init()
        self.__parse_args(active_hips)

        # iterate over steps and run them
        steps = active_hips["steps"]
        module_logger().info("Executing %s steps.." % len(steps))
        for i, step in enumerate(steps):
            hips.notify_active_hips_progress('Step progress', i, len(steps))
            if type(step) is list:
                self.__run_as_group(step)
            else:
                self.__load_and_run_single_step(step)
        hips.notify_active_hips_progress('Step progress', len(steps), len(steps))
        self.__finish_active_hips()

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

    def __run_as_group(self, step):
        """Run a step consisting of multiple substeps - this is used to call HIPS running on the same HIPS app without
        closing the app in between. """
        # dictionary to store successive hips depending on the same app until jointly running them
        same_app_hips = None
        # iterate over steps
        for sub_step in step:
            hips_script = resolve_hips(sub_step)["path"]
            active_hips = hips.load_and_push_hips(hips_script)
            step_args = self.__get_args(sub_step)
            # check if step has parent
            if hasattr(active_hips, "parent"):
                # depending on the parent app, either attach to list of hips belonging to the same app
                # .. or run previous collection of hips and start a new collection of matching hips
                same_app_hips = self.__handle_step_with_parent(active_hips, step_args, same_app_hips)
            else:
                # step has no parent
                if same_app_hips is not None:
                    # reorder hips stack - store newly loaded hips, run previously collected hips belonging to the same
                    # app first, then pop newly loaded hips again
                    new_hips = hips.pop_active_hips()
                    self. __run_same_app_hips(same_app_hips)
                    hips.push_active_hips(new_hips)
                    same_app_hips = None
                self.__run_single_step(active_hips, step_args)
        if same_app_hips is not None:
            # run previously collected hips belonging to the same app
            self.__run_same_app_hips(same_app_hips)

    def __handle_step_with_parent(self, active_hips_step, args, same_app_hips):
        """Handle step with parent in a group of steps"""
        # check if parent is already active
        parent_script = resolve_hips(active_hips_step["parent"])["path"]
        new_parent = True
        if same_app_hips:
            if parent_script != same_app_hips["script"]:
                # this step's parent is different then the currently active parent app, run previous app first
                self.__run_same_app_hips(same_app_hips)
                same_app_hips = None
            else:
                # this step can be executed jointly with previous steps depending on the same app
                new_parent = False
        if new_parent:
            # reorder hips stack - push app first, then child
            first_child = hips.pop_active_hips()
            same_app_hips = {"parent_hips": hips.load_and_push_hips(parent_script), "script": parent_script,
                             "child_hips_list": []}
            hips.push_active_hips(first_child)
        # get arguments for this step
        parent_args, child_args = self.__resolve_args(same_app_hips["parent_hips"], active_hips_step["parent"], args)
        if new_parent:
            # TODO not sure how the parent's arguments should actually be set. we need more use cases to improve this
            same_app_hips["parent_args"] = parent_args
        same_app_hips["child_hips_list"].append([active_hips_step, child_args])
        return same_app_hips

    def __run_same_app_hips(self, same_app_hips):
        """Run multiple HIPS sharing a common parent app on the same app instance"""
        hips_str = ', '.join(item[0]['name'] for item in same_app_hips['child_hips_list'])
        module_logger().info(f"Running HIPS on parent app {same_app_hips['parent_hips']['name']}: {hips_str}")
        self.__handle_hips_with_parent(same_app_hips["parent_hips"], same_app_hips["parent_args"],
                                       same_app_hips["child_hips_list"])

    def __load_and_run_single_step(self, step):
        """Load and run a single HIPS (sharing no app instance with other HIPS)"""
        hips_script = resolve_hips(step)["path"]
        active_hips = hips.load_and_push_hips(hips_script)
        step_args = self.__get_args(step)
        self.__run_single_step(active_hips, step_args)

    def __run_single_step(self, active_hips, args):
        """Run loaded HIPS with given arguments"""
        if hasattr(active_hips, "parent"):
            parent_script = resolve_hips(active_hips["parent"])["path"]
            # reorder hips stack - first parent, then child
            child = hips.pop_active_hips()
            parent_hips = hips.load_and_push_hips(parent_script)
            hips.push_active_hips(child)
            parent_args, child_args = self.__resolve_args(parent_hips, active_hips["parent"], args)
            self.__handle_hips_with_parent(parent_hips, parent_args, [[active_hips, child_args]])
        else:
            self.__handle_standalone_hips(active_hips, args)

    def __handle_standalone_hips(self, active_hips, args):
        """Run loaded HIPS with given arguments and no parent HIPS app"""
        set_environment_name(active_hips)
        set_environment_path(active_hips)
        script_inset = self.init_script
        script_inset += "\nhips.get_active_hips().run()"
        if hasattr(active_hips, "close"):
            script_inset += "\nhips.get_active_hips().close()\n"
        script = create_script(active_hips, script_inset, args)
        self.__run_in_environment_with_own_logger(active_hips, script)
        self.__finish_active_hips()

    def __handle_hips_with_parent(self, parent_hips, parent_args, child_hips_list):
        """Run one or multiple loaded HIPS with given arguments depending on a HIPS app"""
        set_environment_name(parent_hips)
        set_environment_path(parent_hips)
        script = create_hips_with_parent_script(parent_hips, parent_args, child_hips_list, self.init_script)
        self.__run_in_environment_with_own_logger(parent_hips, script)
        self.__finish_hips_with_parent(parent_hips, child_hips_list)

    def __finish_hips_with_parent(self, parent_hips, child_hips_list):
        """Finish both children and common parent HIPS"""
        for item in reversed(child_hips_list):
            child_hips = item[0]
            assert (child_hips['name'] == hips.get_active_hips()['name'])
            hips.pop_active_hips()
        assert (parent_hips['name'] == hips.get_active_hips()['name'])
        self.__finish_active_hips()

    @staticmethod
    def __is_in_catalog(catalog):
        return True if catalog else False

    @staticmethod
    def __finish_active_hips():
        hips.notify_active_hips_finished()
        hips.pop_active_hips()

    @staticmethod
    def __run_in_environment_with_own_logger(active_hips, script):
        """Pushes a new logger to the stack before running the solution and pops it afterwards."""
        hips.notify_hips_started(active_hips)
        hips_logging.configure_logging(
            LogLevel(hips_logging.to_loglevel(hips_logging.get_loglevel_name())), active_hips['name']
        )
        run_in_environment(active_hips["_environment_path"], script)
        hips_logging.pop_active_logger()

    @staticmethod
    def __get_args(step):
        """Parse callable arguments belonging to a step into a list of strings"""
        argv = [""]
        if 'args' in step:
            for param in step["args"]:
                argv.append(f"--{param['name']}={str(param['value']())}")
        return argv

    @staticmethod
    def __resolve_args(parent_hips, parent_description, args):
        """Ugly method to first collect arguments in the parent block of a HIPS, join them with the arguments given in
        `args` and then parse them based on the arguments defined in `parent_hips`. It returns both the arguments
        matching `parent_hips` as well as a list of unknown arguments. """
        if 'args' in parent_description:
            parent_args = parent_description["args"]
            for param in parent_args:
                args.insert(0, f"--{param['name']}={str(param['value'])}")
        parser = argparse.ArgumentParser()
        [parser.add_argument("--" + element["name"]) for element in parent_hips["args"]]
        args_known, args_unknown = parser.parse_known_args(args)
        args_parent = [""]
        args_parent.extend(["--" + element + "=" + getattr(args_known, element) for element in vars(args_known)])
        return args_parent, args_unknown

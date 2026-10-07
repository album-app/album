"""The legacy (album_api_version <= 0.6.1) runner: a required argument may come from pre_test().

This module is a frozen copy of the solution runner, kept so that old solutions keep
running. It carried the same defect as the current runner: trigger_solution_goal() parsed
the command line for the TEST goal before calling pre_test(), so any argument declared
required made argparse exit with "the following arguments are required" before pre_test()
could return the value that would have satisfied it.

The fix must not take away what pre_test() could always do: read the arguments the caller
passed, and the defaults, through get_args() and adapt them. So the command line is still
parsed before pre_test(), only without enforcing `required`, and an invalid one still fails
before pre_test() runs.

The module has no test coverage of its own, so these drive it directly through its own
setup() / get_active_solution() -- the same API a legacy solution script uses -- on a plain
TestCase: the album controller the core unit tests set up is not needed, and its
micromamba dependency would make this file fail to run for the wrong reason.
"""

import os
import sys
import unittest

import album.runner.album_logging
import album.runner.api

# The frozen runner ends with an import-time block -- its "necessary overwrite of the API
# of the old runner" -- that re-points album.runner.api and album.runner.album_logging at
# its own copies of the API. For a legacy solution that is the whole point: script_manager
# writes this module's text into a wrapper script that runs in the solution's own process.
# Imported here, into the album process, the patch would outlive this module and every
# test running afterwards would resolve album_logging.get_active_logger() against the
# frozen runner's own -- always empty -- logger stack, getting the root logger back. That
# silently emptied the task manager's log capture. So snapshot the real API, import, then
# put the real API back; the frozen runner's own functions read its module globals, so the
# tests below still drive the frozen code.
_real_album_api = [
    (module, dict(vars(module)))
    for module in (album.runner.api, album.runner.album_logging)
]

from album.core.utils.runner import backwards_compatibility_0_6_1 as legacy
from album.core.utils.runner.backwards_compatibility_0_6_1 import (
    DefaultValuesRunner,
    Solution,
    SolutionScript,
    get_active_solution,
)

for _module, _attributes in _real_album_api:
    for _name, _value in _attributes.items():
        if getattr(_module, _name, None) is not _value:
            setattr(_module, _name, _value)


class TestLegacyRunnerRequiredArguments(unittest.TestCase):

    def setUp(self):
        # setup() triggers a goal immediately when the runner's action variable is set;
        # clear it so exec() below cannot parse the command line before the test has
        # arranged it. Reset sys.argv for the same reason: the runner appends to it.
        os.environ.pop(DefaultValuesRunner.env_variable_action.value, None)
        sys.argv = [""]
        # A fresh active-solution stack, so a solution left behind by another test is not
        # the one get_active_solution() returns here.
        legacy._active_solution.clear()

    def _exec(self, solution_content):
        namespace = {}
        exec(solution_content, namespace)
        solution = get_active_solution()
        solution.set_script(solution_content)
        return solution

    def test_test_goal_takes_a_required_argument_from_pre_test(self):
        solution = self._exec(
            """
from album.core.utils.runner.backwards_compatibility_0_6_1 import setup, get_active_solution

def pre_test():
    return {"--a1": "fromPreTest"}

def run():
    assert get_active_solution().args().a1 == "fromPreTest", get_active_solution().args().a1

setup(**{
    "group": "tsg",
    "name": "tsn",
    "version": "tsv",
    "pre_test": pre_test,
    "run": run,
    "test": lambda: True,
    "args": [{"name": "a1", "description": "", "required": True}],
})
"""
        )
        # Used to raise SystemExit(2) from argparse before pre_test() was ever called.
        SolutionScript.trigger_solution_goal(solution, Solution.Action.TEST)
        self.assertEqual("fromPreTest", solution.args().a1)

    def test_test_goal_still_refuses_a_missing_required_argument(self):
        """Deferring the parse must not turn a genuinely missing argument into a pass."""
        solution = self._exec(
            """
from album.core.utils.runner.backwards_compatibility_0_6_1 import setup

setup(**{
    "group": "tsg",
    "name": "tsn",
    "version": "tsv",
    "test": lambda: True,
    "args": [{"name": "a1", "description": "", "required": True}],
})
"""
        )
        with self.assertRaises(SystemExit):
            SolutionScript.trigger_solution_goal(solution, Solution.Action.TEST)

    def test_run_goal_still_refuses_a_missing_required_argument(self):
        """RUN is untouched: nothing supplies its arguments but the command line."""
        solution = self._exec(
            """
from album.core.utils.runner.backwards_compatibility_0_6_1 import setup

setup(**{
    "group": "tsg",
    "name": "tsn",
    "version": "tsv",
    "args": [{"name": "a1", "description": "", "required": True}],
})
"""
        )
        with self.assertRaises(SystemExit):
            SolutionScript.trigger_solution_goal(solution, Solution.Action.RUN)

    def test_run_goal_still_reads_an_argument_from_the_command_line(self):
        solution = self._exec(
            """
from album.core.utils.runner.backwards_compatibility_0_6_1 import setup

setup(**{
    "group": "tsg",
    "name": "tsn",
    "version": "tsv",
    "args": [{"name": "a1", "description": ""}],
})
"""
        )
        sys.argv = ["", "--a1", "aValue"]
        SolutionScript.trigger_solution_goal(solution, Solution.Action.RUN)
        self.assertEqual("aValue", solution.args().a1)

    def test_pass_through_arguments_still_work_for_the_test_goal(self):
        solution = self._exec(
            """
from album.core.utils.runner.backwards_compatibility_0_6_1 import setup

setup(**{
    "group": "tsg",
    "name": "tsn",
    "version": "tsv",
    "test": lambda: True,
    "args": "pass-through",
})
"""
        )
        SolutionScript.trigger_solution_goal(solution, Solution.Action.TEST)

    def test_pre_test_can_read_and_adapt_the_command_line_arguments(self):
        """pre_test() sees what the caller passed, and the values it returns win."""
        solution = self._exec(
            """
from album.core.utils.runner.backwards_compatibility_0_6_1 import setup, get_active_solution

def pre_test():
    args = get_active_solution().args()
    return {"--a1": args.a1 + "Adapted", "--a2": str(args.a2 * 2)}

setup(**{
    "group": "tsg",
    "name": "tsn",
    "version": "tsv",
    "pre_test": pre_test,
    "run": lambda: None,
    "test": lambda: True,
    "args": [
        {"name": "a1", "description": "", "required": True},
        {"name": "a2", "description": "", "type": "integer", "default": 1},
    ],
})
"""
        )
        sys.argv = ["", "--a1=fromCommandLine", "--a2=5"]
        SolutionScript.trigger_solution_goal(solution, Solution.Action.TEST)
        self.assertEqual("fromCommandLineAdapted", solution.args().a1)
        self.assertEqual(10, solution.args().a2)

    def test_pre_test_sees_defaults_and_a_required_argument_not_yet_given(self):
        """Nothing passed: pre_test() gets the defaults, and None for what it must supply."""
        solution = self._exec(
            """
from album.core.utils.runner.backwards_compatibility_0_6_1 import setup, get_active_solution

def pre_test():
    args = get_active_solution().args()
    assert args.a1 is None, args.a1
    assert args.a2 == 1, args.a2
    return {"--a1": "fixture"}

setup(**{
    "group": "tsg",
    "name": "tsn",
    "version": "tsv",
    "pre_test": pre_test,
    "run": lambda: None,
    "test": lambda: True,
    "args": [
        {"name": "a1", "description": "", "required": True},
        {"name": "a2", "description": "", "type": "integer", "default": 1},
    ],
})
"""
        )
        SolutionScript.trigger_solution_goal(solution, Solution.Action.TEST)
        self.assertEqual("fixture", solution.args().a1)
        self.assertEqual(1, solution.args().a2)

    def test_test_goal_refuses_an_invalid_command_line_before_pre_test_runs(self):
        """A typo on the command line fails fast, not after pre_test() did its work."""
        solution = self._exec(
            """
from album.core.utils.runner.backwards_compatibility_0_6_1 import setup

def pre_test():
    raise AssertionError("pre_test() ran although the command line was invalid")

setup(**{
    "group": "tsg",
    "name": "tsn",
    "version": "tsv",
    "pre_test": pre_test,
    "test": lambda: True,
    "args": [{"name": "a1", "description": ""}],
})
"""
        )
        sys.argv = ["", "--typo=1"]
        with self.assertRaises(SystemExit):
            SolutionScript.trigger_solution_goal(solution, Solution.Action.TEST)


if __name__ == "__main__":
    unittest.main()

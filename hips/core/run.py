from hips.core.controller.run_manager import RunManager
from hips_runner import logging

# ToDo: environment purge method
# ToDo: reusable versioned environments?
# ToDo: test for windows
# ToDo: subprocess logging (https://www.endpoint.com/blog/2015/01/28/getting-realtime-output-using-python)
# ToDo: solutions should not run in hips.yml for comp. reasons. Maybe check that?
# ToDo: install helper - methods (pip install) (git-download) (java-dependcies)


module_logger = logging.get_active_logger

run_manager = RunManager()


def run(args):
    run_manager.run(args.path)

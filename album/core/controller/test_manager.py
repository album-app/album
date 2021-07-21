from queue import Queue

from album.core.concept.singleton import Singleton
from album.core.controller.resolve_manager import ResolveManager
from album.core.controller.run_manager import RunManager
from album_runner import logging
from album_runner.logging import LogLevel

module_logger = logging.get_active_logger


class TestManager(metaclass=Singleton):
    """Class managing testing routine of a solution. Similar to the installation process, a configured \"test \"
    routine of a solution is executed in the target environment (The conda environment the solution lives in).
    Solutions must be installed to run their testing routine.

     Attributes:
         resolve_manager:
            Holding all configured catalogs. Resolves inside our outside catalogs.

    """
    # singletons
    resolve_manager = None
    run_manager = None

    def __init__(self):
        self.resolve_manager = ResolveManager()
        self.run_manager = RunManager()

    def test(self, path):
        """Function corresponding to the `test` subcommand of `album`."""
        try:
            resolve, active_solution = self.resolve_manager.resolve_installed_and_load(path)
        except ValueError:
            raise ValueError("Solution points to a local file which has not been installed yet. "
                             "Please point to an installation from the catalog or install the solution. "
                             "Aborting...")

        if not resolve["catalog"]:
            module_logger().debug('album loaded locally: %s...' % str(active_solution))
        else:
            module_logger().debug('album loaded from catalog: %s...' % str(active_solution))

        self._test(active_solution)

        module_logger().info('Test run for %s!' % active_solution['name'])

    def _test(self, active_solution):
        if active_solution['pre_test'] and callable(active_solution['pre_test']) \
                and active_solution['test'] and callable(active_solution['test']):
            module_logger().debug('Creating test script...')

            # set init of run_manager to include pre_test call and argument parsing before run
            self.run_manager.init_script = "\nd = get_active_solution().pre_test()\n"
            self.run_manager.init_script += "\nsys.argv = sys.argv + [\"=\".join([c, d[c]]) for c in d]\n"

            # parse args again after pre_test() routine if necessary.
            if not active_solution["args"] == "pass-through":
                self.run_manager.init_script += "\nparser.parse_args()\n"

            # prepare run_script
            que = Queue()
            self.run_manager.build_queue(active_solution, que, False)  # do not run queue immediately
            _, scripts = que.get(block=False)

            # add test_routine to script
            if len(scripts) > 1:
                scripts.append("\nget_active_solution().test()\n")
            else:
                scripts[0] += "\nget_active_solution().test()\n"

            module_logger().debug('Calling test routine specified in solution...')
            logging.configure_logging(
                LogLevel(logging.to_loglevel(logging.get_loglevel_name())), active_solution['name']
            )
            active_solution.environment.run_scripts(scripts)
            logging.pop_active_logger()
        else:
            module_logger().warning('No \"test\" routine configured for solution %s! Skipping...' % active_solution['name'])

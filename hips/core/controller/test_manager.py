from queue import Queue

from hips.core import load
from hips.core.concept.singleton import Singleton
from hips.core.controller.run_manager import RunManager
from hips.core.model.catalog_collection import HipsCatalogCollection
from hips_runner import logging
from hips_runner.logging import LogLevel

module_logger = logging.get_active_logger


class TestManager(metaclass=Singleton):
    """Class managing testing routine of a solution. Similar to the installation process, a configured \"test \"
    routine of a solution is executed in the target environment (The conda environment the solution lives in).
    Solutions must be installed to run their testing routine.

     Attributes:
         catalog_collection:
            Holds all the catalogs of the HIPS framework installation.

    """
    # singletons
    catalog_collection = None
    run_manager = None

    def __init__(self, catalog_collection=None):
        self.catalog_collection = HipsCatalogCollection() if not catalog_collection else catalog_collection
        self.run_manager = RunManager(self.catalog_collection)

    def test(self, path):
        """Function corresponding to the `test` subcommand of `hips`."""
        resolve = self.catalog_collection.resolve_from_str(path, download=False)

        if not resolve["catalog"]:
            if not (resolve['path'].is_file() and resolve['path'].stat().st_size > 0):
                raise RuntimeError("Please install solution first!")

        active_hips = load(resolve["path"])

        if not resolve["catalog"]:
            module_logger().debug('hips loaded locally: %s...' % str(active_hips))
        else:
            module_logger().debug('hips loaded from catalog: %s...' % str(active_hips))

        self._test(active_hips)

        module_logger().info('Test run for %s!' % active_hips['name'])

    def _test(self, active_hips):
        if active_hips['pre_test'] and callable(active_hips['pre_test']) \
                and active_hips['test'] and callable(active_hips['test']):
            module_logger().debug('Creating test script...')

            # set init of run_manager to include pre_test call and argument parsing before run
            self.run_manager.init_script = "\nd = get_active_hips().pre_test()\n"
            self.run_manager.init_script += "\nsys.argv = sys.argv + [\"=\".join([c, d[c]]) for c in d]\n"

            # parse args again after pre_test() routine if necessary.
            if not active_hips["args"] == "pass-through":
                self.run_manager.init_script += "\nparser.parse_args()\n"

            # prepare run_script
            que = Queue()
            self.run_manager.build_queue(active_hips, que, False)  # do not run queue immediately
            _, scripts = que.get(block=False)

            # add test_routine to script
            if len(scripts) > 1:
                scripts.append("\nget_active_hips().test()\n")
            else:
                scripts[0] += "\nget_active_hips().test()\n"

            module_logger().debug('Calling test routine specified in solution...')
            logging.configure_logging(
                LogLevel(logging.to_loglevel(logging.get_loglevel_name())), active_hips['name']
            )
            active_hips.environment.run_scripts(scripts)
            logging.pop_active_logger()
        else:
            module_logger().warning('No \"test\" routine configured for solution %s! Skipping...' % active_hips['name'])

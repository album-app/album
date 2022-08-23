from queue import Queue
from typing import List

import pkg_resources

from album.runner import album_logging

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.run_manager import IRunManager
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.model.default_values import DefaultValues
from album.core.model.event import Event
from album.runner.core.api.model.solution import ISolution
from album.runner.core.model.script_creator import ScriptCreatorRun

module_logger = album_logging.get_active_logger


class SolutionGroup:
    def __init__(
        self,
        parent_parsed_args=None,
        parent: ICollectionSolution = None,
        steps_solution=None,
        steps=None,
    ):
        if parent_parsed_args is None:
            parent_parsed_args = [None]
        if steps_solution is None:
            steps_solution = []
        if steps is None:
            steps = []
        self.parent_parsed_args = parent_parsed_args
        self.parent = parent
        self.steps_solution: List[
            ISolution
        ] = steps_solution  # The solution objects of all steps.

        self.steps = (
            steps  # The step description of the step. Must hold the argument keyword.
        )

    def __eq__(self, o: object) -> bool:
        return (
            isinstance(o, SolutionGroup)
            and o.parent.coordinates() == self.parent.coordinates()
            and o.steps_solution == self.steps_solution
            and o.steps == self.steps
        )


class RunManager(IRunManager):
    def __init__(self, album: IAlbumController):
        self.album = album

        self.init_script = ""

    def run(self, solution_to_resolve: str, run_immediately=False, argv=None):
        """Run an already loaded solution."""
        resolve_result = self.album.collection_manager().resolve_installed_and_load(
            solution_to_resolve
        )
        coordinates = resolve_result.loaded_solution().coordinates()
        if not resolve_result.catalog:
            module_logger().debug("solution loaded locally: %s..." % str(coordinates))
        else:
            module_logger().debug(
                'solution loaded from catalog: "%s"...' % str(coordinates)
            )
        module_logger().debug('Initializing script to run "%s"' % coordinates)

        self.load_plugins(resolve_result)

        if argv is None:
            argv = [""]

        # pushing album and their scripts to a queue
        que = Queue()

        # builds the queue
        self.album.script_manager().build_queue(
            resolve_result, que, ScriptCreatorRun(), run_immediately, argv
        )

        self.album.event_manager().publish(
            Event(DefaultValues.before_run_event_name.value),
            resolve_result.coordinates(),
        )

        # runs the queue
        try:
            self.album.script_manager().run_queue(que)
        finally:
            self.album.event_manager().publish(
                Event(DefaultValues.after_run_event_name.value),
                resolve_result.coordinates(),
            )

        module_logger().debug(
            'Finished running script for solution "%s"' % coordinates.name()
        )

    def load_plugins(self, resolve_result):
        # process solution plugins
        module_logger().debug("Processing plugins...")
        if "dependencies" in resolve_result.loaded_solution().setup():
            deps = resolve_result.loaded_solution().setup()["dependencies"]
            if "plugins" in deps:
                module_logger().debug(
                    "Processing solution plugins: %s" % deps["plugins"]
                )
                available_plugins = pkg_resources.iter_entry_points("plugins_album")
                for plugin in deps["plugins"]:
                    found = False
                    for entry_point in available_plugins:
                        if entry_point.name == plugin["id"]:
                            module_logger().debug(
                                "Found plugin %s, initializing activation.."
                                % plugin["id"]
                            )
                            plugin_call = entry_point.load()
                            plugin_args = plugin["args"] if "args" in plugin else {}
                            from album.api import Album

                            plugin_call(
                                Album(self.album),
                                resolve_result.coordinates(),
                                plugin_args,
                            )
                            module_logger().debug("Plugin %s activated." % plugin["id"])
                            found = True
                            break
                    if not found:
                        raise LookupError(
                            "Cannot find plugin %s - please make sure the package providing this plugin "
                            "is installed into the album environment." % plugin["id"]
                        )
        module_logger().debug("Plugins processed.")

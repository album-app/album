import json
import sys

from flask import Flask, request
from werkzeug.exceptions import abort

from album.core.concept.singleton import Singleton
from album.core.controller.catalog_manager import CatalogManager
from album.core.controller.install_manager import InstallManager
from album.core.controller.remove_manager import RemoveManager
from album.core.controller.run_manager import RunManager
from album.core.controller.search_manager import SearchManager
from album.core.controller.task_manager import TaskManager
from album.core.controller.test_manager import TestManager
from album.core.model.catalog_collection import CatalogCollection, module_logger
from album.core.model.configuration import Configuration
from album.core.model.default_values import DefaultValues
from album.core.model.solutions_db import SolutionsDb
from album.core.model.task import Task
from album_runner import logging

module_logger = logging.get_active_logger


class AlbumServer(metaclass=Singleton):

    port = DefaultValues.server_port

    # load singletons
    configuration = None
    catalog_collection = None
    resolve_manager = None
    catalog_manager = None
    install_manager = None
    remove_manager = None
    run_manager = None
    search_manager = None
    test_manager = None
    task_manager = None
    solutions_db = None

    app = None

    def __init__(self, port):
        self.setup(port)

    def setup(self, port):
        self.port = port
        self.configuration = Configuration()
        self.catalog_collection = CatalogCollection()
        self.catalog_manager = CatalogManager()
        self.install_manager = InstallManager()
        self.remove_manager = RemoveManager()
        self.run_manager = RunManager()
        self.search_manager = SearchManager()
        self.test_manager = TestManager()
        self.task_manager = TaskManager()
        self.solutions_db = SolutionsDb()

    def start(self, test_config=None):
        module_logger().info('Starting server..')
        self.init_server(test_config)
        self.app.run(port=self.port)

    def init_server(self, test_config=None):
        self.app = Flask(__name__, instance_relative_config=True)
        if test_config is not None:
            self.app.config.update(test_config)
        self._set_routes()
        return self.app

    def _set_routes(self):
        @self.app.route("/")
        def hello_world():
            return {"message": "Hello World"}

        @self.app.route("/config")
        def get_config():
            return {
                "album_config_path": str(self.catalog_collection.config_file_path),
                "album_config": self.catalog_collection.config_file_dict,
                "cache_base": str(self.configuration.base_cache_path),
                "cache_solutions": str(self.configuration.cache_path_solution),
                "cache_apps": str(self.configuration.cache_path_app),
                "cache_downloads": str(self.configuration.cache_path_download)
            }

        @self.app.route("/index")
        def get_index():
            catalog_dict = {}
            for catalog in self.catalog_collection.catalogs:
                self._write_catalog_to_dict(catalog_dict, catalog)
                catalog_dict[catalog.id]["solutions"] = catalog.catalog_index.get_leaves_dict_list()
            return catalog_dict

        @self.app.route("/catalogs")
        def get_catalogs():
            catalog_dict = {}
            for catalog in self.catalog_collection.catalogs:
                self._write_catalog_to_dict(catalog_dict, catalog)
            return catalog_dict

        @self.app.route("/recently-launched")
        def get_recently_launched_solutions():
            return {"solutions": self.solutions_db.get_recently_launched_solutions()}

        @self.app.route("/recently-installed")
        def get_recently_installed_solutions():
            return {"solutions": self.solutions_db.get_recently_installed_solutions()}

        @self.app.route('/run/<group>/<name>/<version>', defaults={'catalog': None})
        @self.app.route('/run/<catalog>/<group>/<name>/<version>')
        def run(catalog, group, name, version):
            module_logger().info(f"Server call: /run/{catalog}/{group}/{name}/{version}")
            task = self._run_solution_method_async(catalog, group, name, version, self.run_manager.run)
            return {"id": task.id, "msg": "process started"}

        @self.app.route('/install/<group>/<name>/<version>', defaults={'catalog': None})
        @self.app.route('/install/<catalog>/<group>/<name>/<version>')
        def install(catalog, group, name, version):
            task = self._run_solution_method_async(catalog, group, name, version, self.install_manager.install)
            return {"id": task.id, "msg": "process started"}

        @self.app.route('/remove/<group>/<name>/<version>', defaults={'catalog': None})
        @self.app.route('/remove/<catalog>/<group>/<name>/<version>')
        def remove(catalog, group, name, version):
            task = self._run_solution_method_async(catalog, group, name, version, self.remove_manager.remove)
            return {"id": task.id, "msg": "process started"}

        @self.app.route('/test/<group>/<name>/<version>', defaults={'catalog': None})
        @self.app.route('/test/<catalog>/<group>/<name>/<version>')
        def test(catalog, group, name, version):
            task = self._run_solution_method_async(catalog, group, name, version, self.test_manager.test)
            return {"id": task.id, "msg": "process started"}

        @self.app.route('/status/<catalog>/<group>/<name>/<version>')
        def status_solution(catalog, group, name, version):
            installed = self.solutions_db.is_installed(catalog, group, name, version)
            res = {
                "installed": installed
            }
            return res

        @self.app.route('/status/<task_id>')
        def status_task(task_id):
            task = self.task_manager.get_task(str(task_id))
            if task is None:
                abort(404, description=f"Task not found with id {task_id}")
            return self.task_manager.get_status(task)

        @self.app.route('/add-catalog')
        def add_catalog():
            url = request.args.get("path")
            self.catalog_manager.add(url)
            return {}

        @self.app.route('/remove-catalog')
        def remove_catalog():
            url = request.args.get("path")
            self.catalog_manager.remove(url)
            return {}

        @self.app.route('/search/<keywords>')
        def search(keywords):
            return self.search_manager.search(keywords)

        @self.app.route('/shutdown', methods=['GET'])
        def shutdown():
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                raise RuntimeError('Not running with the Werkzeug Server')
            func()
            return 'Server shutting down...'

    @staticmethod
    def _write_catalog_to_dict(catalog_dict, catalog):
        catalog_dict[catalog.id] = {}
        catalog_dict[catalog.id]["src"] = str(catalog.src) if catalog.src else None
        catalog_dict[catalog.id]["path"] = str(catalog.path) if catalog.path else None
        catalog_dict[catalog.id]["is_local"] = catalog.is_local

    def _run_solution_method(self, catalog, group, name, version, method):
        solution_path = self.get_solution_path_or_abort(catalog, group, name, version)
        sys.argv = self._get_arguments(request.get_json(), solution_path)
        return method(solution_path)

    def _run_solution_method_async(self, catalog, group, name, version, method):
        task = Task()
        if catalog is None:
            task.solution_path = ":".join([group, name, version])
        else:
            task.solution_path = ":".join([catalog, group, name, version])
        task.sysarg = self._get_arguments(request.get_json(), task.solution_path)
        task.method = method
        self.task_manager.register_task(task)
        return task

    @staticmethod
    def _get_arguments(args_json, solution_path):
        command_args = [str(solution_path)]
        if args_json:
            request_data = json.loads(args_json)
            for key in request_data:
                command_args.append(f"--{key}")
                command_args.append(str(request_data[key]))
        return command_args

    def get_solution_path_or_abort(self, catalog, group, name, version):
        solution_path = self._get_solution_path(catalog, group, name, version)
        if solution_path is None:
            abort(404, description=f"Solution not found: {catalog}:{group}:{name}:{version}")
        return solution_path

    def _get_solution_path(self, catalog, group, name, version):
        if catalog is None:
            solution = self.catalog_collection.resolve_dependency({"group": group, "name": name, "version": version})
        else:
            solution = self.catalog_collection.resolve_directly(catalog_id=catalog, group=group, name=name, version=version)
        if solution is None:
            module_logger().error(f"Solution not found: {catalog}:{group}:{name}:{version}")
            return None
        else:
            return str(solution['path'])


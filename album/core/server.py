import json
from distutils import util
from pathlib import Path

from flask import Flask, request
from werkzeug.exceptions import abort

from album.core.concept.singleton import Singleton
from album.core.controller.collection_manager import CollectionManager
from album.core.controller.deploy_manager import DeployManager
from album.core.controller.install_manager import InstallManager
from album.core.controller.remove_manager import RemoveManager
from album.core.controller.run_manager import RunManager
from album.core.controller.search_manager import SearchManager
from album.core.controller.task_manager import TaskManager
from album.core.controller.test_manager import TestManager
from album.core.model.configuration import Configuration
from album.core.model.default_values import DefaultValues
from album.core.model.group_name_version import GroupNameVersion
from album.core.model.task import Task
from album_runner import logging

module_logger = logging.get_active_logger


class AlbumServer(metaclass=Singleton):

    port = DefaultValues.server_port

    app = None

    def __init__(self, port):
        self.setup(port)

    def setup(self, port):
        self.port = port

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
                "album_config_path": str(CollectionManager().catalog_collection.config_file_path),
                "album_config": CollectionManager().catalog_collection.config_file_dict,
                "cache_base": str(Configuration().base_cache_path),
                "cache_solutions": str(Configuration().cache_path_solution),
                "cache_apps": str(Configuration().cache_path_app),
                "cache_downloads": str(Configuration().cache_path_download)
            }

        @self.app.route("/index")
        def get_index():
            return CollectionManager().get_index_as_dict()

        @self.app.route("/catalogs")
        def get_catalogs():
            return CollectionManager().catalogs().get_all_as_dict()

        @self.app.route("/recently-launched")
        def get_recently_launched_solutions():
            return {"solutions": CollectionManager().catalog_collection.get_recently_launched_solutions()}

        @self.app.route("/recently-installed")
        def get_recently_installed_solutions():
            return {"solutions": CollectionManager().catalog_collection.get_recently_installed_solutions()}

        @self.app.route('/run/<group>/<name>/<version>', defaults={'catalog': None})
        @self.app.route('/run/<catalog>/<group>/<name>/<version>')
        def run(catalog, group, name, version):
            module_logger().info(f"Server call: /run/{catalog}/{group}/{name}/{version}")
            task = self._run_solution_method_async(catalog, GroupNameVersion(group, name, version), RunManager().run)
            return {"id": task.id, "msg": "process started"}

        @self.app.route('/install/<group>/<name>/<version>', defaults={'catalog': None})
        @self.app.route('/install/<catalog>/<group>/<name>/<version>')
        def install(catalog, group, name, version):
            task = self._run_solution_method_async(catalog, GroupNameVersion(group, name, version), InstallManager().install)
            return {"id": task.id, "msg": "process started"}

        @self.app.route('/remove/<group>/<name>/<version>', defaults={'catalog': None})
        @self.app.route('/remove/<catalog>/<group>/<name>/<version>')
        def remove(catalog, group, name, version):
            task = self._run_solution_method_async(catalog, GroupNameVersion(group, name, version), RemoveManager().remove)
            return {"id": task.id, "msg": "process started"}

        @self.app.route('/test/<group>/<name>/<version>', defaults={'catalog': None})
        @self.app.route('/test/<catalog>/<group>/<name>/<version>')
        def test(catalog, group, name, version):
            task = self._run_solution_method_async(catalog, GroupNameVersion(group, name, version), TestManager().test)
            return {"id": task.id, "msg": "process started"}

        @self.app.route('/deploy')
        def deploy():
            solution_path = request.args.get("path")
            catalog_name = request.args.get("catalog_name")
            if solution_path is None:
                abort(404, description=f"`path` argument missing")
            if not Path(solution_path).exists():
                abort(404, description=f"Solution not found: {solution_path}")
            if catalog_name is None:
                abort(404, description=f"`catalog_name` argument missing")
            dryrun = bool(util.strtobool(request.args.get("dryrun", default="false")))
            trigger_pipeline = False
            task = Task()
            task.args = (solution_path, catalog_name, dryrun, trigger_pipeline)
            task.method = DeployManager().deploy
            TaskManager().register_task(task)
            return {"id": task.id, "msg": "process started"}

        @self.app.route('/status/<catalog>/<group>/<name>/<version>')
        def status_solution(catalog, group, name, version):
            try:
                catalog_manager = CollectionManager()
                catalog_id = catalog_manager.catalog_handler.get_by_name(catalog).catalog_id
                installed = catalog_manager.catalog_collection.is_installed(catalog_id, GroupNameVersion(group, name, version))
                return {
                    "installed": installed
                }
            except LookupError as e:
                abort(404, description=f"Solution not found")

        @self.app.route('/status/<task_id>')
        def status_task(task_id):
            task = TaskManager().get_task(str(task_id))
            if task is None:
                abort(404, description=f"Task not found with id {task_id}")
            return TaskManager().get_status(task)

        @self.app.route('/add-catalog')
        def add_catalog():
            url = request.args.get("src")
            name = request.args.get("name")
            catalog_id = CollectionManager().catalogs().add_by_src(url).catalog_id
            return {"catalog_id": catalog_id}

        @self.app.route('/remove-catalog')
        def remove_catalog():
            url = request.args.get("src", default=None)
            name = request.args.get("name", default=None)
            if name is None:
                CollectionManager().catalogs().remove_from_index_by_src(url)
            else:
                CollectionManager().catalogs().remove_from_index_by_name(name)
            return {}

        @self.app.route('/search/<keywords>')
        def search(keywords):
            return SearchManager().search(keywords)

        @self.app.route('/shutdown', methods=['GET'])
        def shutdown():
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                raise RuntimeError('Not running with the Werkzeug Server')
            func()
            return 'Server shutting down...'

    def _run_solution_method_async(self, catalog, group_name_version: GroupNameVersion, method):
        task = Task()
        if catalog is None:
            solution_path = str(group_name_version)
        else:
            solution_path = ":".join([catalog, str(group_name_version)])
        task.args = (solution_path, )
        task.sysarg = self._get_arguments(request.get_json(), solution_path)
        task.method = method
        TaskManager().register_task(task)
        return task

    def _run_path_method_async(self, path, args, method):
        task = Task()
        command_args = [str(path)]
        for arg in args:
            command_args.append(arg)
        task.sysarg = command_args
        task.method = method
        TaskManager().register_task(task)
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


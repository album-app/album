from distutils import util
from pathlib import Path

from flask import Flask, request
from werkzeug.exceptions import abort

from album.api import Album
from album.core.concept.singleton import Singleton
from album.core.controller.clone_manager import CloneManager
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.controller.deploy_manager import DeployManager
from album.core.controller.install_manager import InstallManager
from album.core.controller.run_manager import RunManager
from album.core.controller.search_manager import SearchManager
from album.core.controller.task_manager import TaskManager
from album.core.controller.test_manager import TestManager
from album.core.model.coordinates import Coordinates
from album.core.model.default_values import DefaultValues
from album.core.model.task import Task
from album.runner import logging

module_logger = logging.get_active_logger


class AlbumServer(metaclass=Singleton):
    port = DefaultValues.server_port.value
    host = DefaultValues.server_port.value

    app = None

    def __init__(self, port: int, host: str = None):
        self.port = port
        self.host = host
        self.album = None

    def setup(self, album: Album = None):
        if album:
            self.album = album
        else:
            self.album = Album()

    def start(self, test_config=None):
        module_logger().info('Starting server..')
        self.init_server(test_config)
        self.app.run(port=self.port, host=self.host)

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
                "cache_base": str(self.album.configuration().base_cache_path),
                "cache_solutions": str(self.album.configuration().cache_path_solution),
                "cache_apps": str(self.album.configuration().cache_path_app),
                "cache_downloads": str(self.album.configuration().cache_path_download)
            }

        @self.app.route("/index")
        def get_index():
            return self.album.collection_manager().get_index_as_dict()

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
            args = self._get_arguments(request.args)
            task = self._run_solution_method_async(catalog, Coordinates(group, name, version), RunManager().run, [True, args])
            return {"id": task.id, "msg": "process started"}

        @self.app.route('/install/<group>/<name>/<version>', defaults={'catalog': None})
        @self.app.route('/install/<catalog>/<group>/<name>/<version>')
        def install(catalog, group, name, version):
            task = self._run_solution_method_async(
                catalog,
                Coordinates(group, name, version),
                InstallManager().install
            )
            return {"id": task.id, "msg": "process started"}

        @self.app.route('/uninstall/<group>/<name>/<version>', defaults={'catalog': None})
        @self.app.route('/uninstall/<catalog>/<group>/<name>/<version>')
        def uninstall(catalog, group, name, version):
            task = self._run_solution_method_async(
                catalog,
                Coordinates(group, name, version),
                InstallManager().uninstall
            )
            return {"id": task.id, "msg": "process started"}

        @self.app.route('/test/<group>/<name>/<version>', defaults={'catalog': None})
        @self.app.route('/test/<catalog>/<group>/<name>/<version>')
        def test(catalog, group, name, version):
            task = self._run_solution_method_async(catalog, Coordinates(group, name, version), TestManager().test)
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

        @self.app.route('/clone/<group>/<name>/<version>', defaults={'catalog': None})
        @self.app.route('/clone/<catalog>/<group>/<name>/<version>')
        def clone_solution(catalog, group, name, version):
            target_dir = request.args.get("target_dir")
            new_name = request.args.get("name")
            if target_dir is None:
                abort(404, description=f"`target_dir` argument missing")
            if new_name is None:
                abort(404, description=f"`name` argument missing")
            args = [target_dir, new_name]
            task = self._run_solution_method_async(
                catalog,
                Coordinates(group, name, version),
                CloneManager().clone, args
            )
            return {"id": task.id, "msg": "process started"}

        @self.app.route('/clone')
        def clone_solution_py_path():
            target_dir = request.args.get("target_dir")
            name = request.args.get("name")
            path = request.args.get("path")
            if target_dir is None:
                abort(404, description=f"`target_dir` argument missing")
            if name is None:
                abort(404, description=f"`name` argument missing")
            if path is None:
                abort(404, description=f"`path` argument missing")
            args = [target_dir, name]
            task = Task()
            task_args = [path]
            if args:
                for arg in args:
                    task_args.append(arg)
            task.args = tuple(task_args)
            task.method = CloneManager().clone
            TaskManager().register_task(task)
            return {"id": task.id, "msg": "process started"}

        @self.app.route('/clone/<template_name>')
        def clone_catalog(template_name):
            target_dir = request.args.get("target_dir")
            name = request.args.get("name")
            if target_dir is None:
                abort(404, description=f"`target_dir` argument missing")
            if name is None:
                abort(404, description=f"`name` argument missing")
            task = Task()
            task.args = tuple([template_name, target_dir, name])
            task.method = CloneManager().clone
            TaskManager().register_task(task)
            return {"id": task.id, "msg": "process started"}

        @self.app.route('/status/<catalog>/<group>/<name>/<version>')
        def status_solution(catalog, group, name, version):
            try:
                collection_manager = CollectionManager()
                catalog_id = collection_manager.catalog_handler.get_by_name(catalog).catalog_id
                installed = collection_manager.catalog_collection.is_installed(
                    catalog_id,
                    Coordinates(group, name, version)
                )
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
                CollectionManager().catalogs().remove_from_collection_by_src(url)
            else:
                CollectionManager().catalogs().remove_from_collection_by_name(name)
            return {}

        @self.app.route('/upgrade')
        def upgrade():
            src = request.args.get("src", default=None)
            name = request.args.get("name", default=None)
            dry_run = request.args.get("dry_run", default=False)
            if name is None and src is None:
                res = CollectionManager().catalogs().update_collection(dry_run=dry_run)
            elif name is None:
                catalog = CollectionManager().catalogs().get_by_src(src)
                res = CollectionManager().catalogs().update_collection(catalog_name=catalog.name, dry_run=dry_run)
            else:
                res = CollectionManager().catalogs().update_collection(catalog_name=name, dry_run=dry_run)
            r = []
            for update_obj in res:
                r.append(update_obj.as_dict())
            return {"changes": r}

        @self.app.route('/update')
        def update():
            src = request.args.get("src", default=None)
            name = request.args.get("name", default=None)
            if name is None and src is None:
                CollectionManager().catalogs().update_any()
            elif name is None:
                catalog = CollectionManager().catalogs().get_by_src(src)
                CollectionManager().catalogs().update_any(catalog.name)
            else:
                CollectionManager().catalogs().update_any(name)
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

    @staticmethod
    def task_manager() -> TaskManager:
        return TaskManager()

    @staticmethod
    def _run_solution_method_async(catalog, group_name_version: Coordinates, method, args=None):
        task = Task()
        if catalog is None:
            solution_path = str(group_name_version)
        else:
            solution_path = ":".join([catalog, str(group_name_version)])
        task_args = [solution_path]
        if args:
            for arg in args:
                task_args.append(arg)
        task.args = tuple(task_args)
        task.method = method
        TaskManager().register_task(task)
        return task

    @staticmethod
    def _get_arguments(args_json):
        command_args = [""]
        if args_json:
            for key in args_json:
                command_args.append(f"--{key}")
                command_args.append(str(args_json[key]))
        return command_args

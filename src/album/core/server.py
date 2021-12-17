from distutils import util
from pathlib import Path
from typing import Optional

from flask import Flask, request
from werkzeug.exceptions import abort

import album
from album.core.api.album import IAlbum
from album.core.api.controller.task_manager import ITaskManager
from album.core.model.default_values import DefaultValues
from album.core.model.task import Task
from album.runner import album_logging
from album.runner.core.model.coordinates import Coordinates

module_logger = album_logging.get_active_logger


class AlbumServer:
    port = DefaultValues.server_port.value
    host = DefaultValues.server_port.value

    app = None

    def __init__(self, port: int, host: str = None):
        self.port = port
        self.host = host
        self.album_instance: Optional[IAlbum] = None

    def setup(self, album_instance: IAlbum):
        self.album_instance = album_instance

    def start(self, test_config=None):
        module_logger().info('Starting server...')
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
        def get_version():
            return {
                "version": album.core.__version__,
                "author": album.core.__author__,
                "email": album.core.__email__
            }

        @self.app.route("/config")
        def get_config():
            return {
                "cache_base": str(self.album_instance.configuration().base_cache_path()),
                "cache_tmp_internal": str(self.album_instance.configuration().cache_path_tmp_internal()),
                "cache_tmp_user": str(self.album_instance.configuration().cache_path_tmp_user()),
                "cache_apps": str(self.album_instance.configuration().cache_path_app()),
                "cache_downloads": str(self.album_instance.configuration().cache_path_download())
            }

        @self.app.route("/index")
        def get_index():
            index_dict = self.album_instance.collection_manager().get_index_as_dict()
            return index_dict

        @self.app.route("/catalogs")
        def get_catalogs():
            return self.album_instance.collection_manager().catalogs().get_all_as_dict()

        @self.app.route("/recently-launched")
        def get_recently_launched_solutions():
            solutions = []
            for solution in self.album_instance.collection_manager().get_collection_index().get_recently_launched_solutions():
                solutions.append({
                    'setup': solution.setup(),
                    'internal': solution.internal()
                })
            return {'solutions': solutions}

        @self.app.route("/recently-installed")
        def get_recently_installed_solutions():
            solutions = []
            for solution in self.album_instance.collection_manager().get_collection_index().get_recently_installed_solutions():
                solutions.append({
                    'setup': solution.setup(),
                    'internal': solution.internal()
                })
            return {'solutions': solutions}

        @self.app.route('/run/<group>/<name>/<version>', defaults={'catalog': None})
        @self.app.route('/run/<catalog>/<group>/<name>/<version>')
        def run(catalog, group, name, version):
            args = self._get_arguments(request.args)
            task = self._run_solution_method_async(catalog, Coordinates(group, name, version),
                                                   self.album_instance.run_manager().run,
                                                   [True, args])
            return {"id": task.id(), "msg": "process started"}

        @self.app.route('/install/<group>/<name>/<version>', defaults={'catalog': None})
        @self.app.route('/install/<catalog>/<group>/<name>/<version>')
        def install(catalog, group, name, version):
            task = self._run_solution_method_async(
                catalog,
                Coordinates(group, name, version),
                self.album_instance.install_manager().install
            )
            return {"id": task.id(), "msg": "process started"}

        @self.app.route('/uninstall/<group>/<name>/<version>', defaults={'catalog': None})
        @self.app.route('/uninstall/<catalog>/<group>/<name>/<version>')
        def uninstall(catalog, group, name, version):
            task = self._run_solution_method_async(
                catalog,
                Coordinates(group, name, version),
                self.album_instance.install_manager().uninstall
            )
            return {"id": task.id(), "msg": "process started"}

        @self.app.route('/test/<group>/<name>/<version>', defaults={'catalog': None})
        @self.app.route('/test/<catalog>/<group>/<name>/<version>')
        def test(catalog, group, name, version):
            task = self._run_solution_method_async(catalog, Coordinates(group, name, version),
                                                   self.album_instance.test_manager().test)
            return {"id": task.id(), "msg": "process started"}

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
            task._args = (solution_path, catalog_name, dryrun, trigger_pipeline)
            task._method = self.album_instance.deploy_manager().deploy
            self.task_manager().register_task(task)
            return {"id": task.id(), "msg": "process started"}

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
                self.album_instance.clone_manager().clone, args
            )
            return {"id": task.id(), "msg": "process started"}

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
            task._args = tuple(task_args)
            task._method = self.album_instance.clone_manager().clone
            self.task_manager().register_task(task)
            return {"id": task.id(), "msg": "process started"}

        @self.app.route('/clone/<template_name>')
        def clone_catalog(template_name):
            target_dir = request.args.get("target_dir")
            name = request.args.get("name")
            if target_dir is None:
                abort(404, description=f"`target_dir` argument missing")
            if name is None:
                abort(404, description=f"`name` argument missing")
            task = Task()
            task._args = tuple([template_name, target_dir, name])
            task._method = self.album_instance.clone_manager().clone
            self.task_manager().register_task(task)
            return {"id": task.id(), "msg": "process started"}

        @self.app.route('/status/<catalog>/<group>/<name>/<version>')
        def status_solution(catalog, group, name, version):
            try:
                collection_manager = self.album_instance.collection_manager()
                catalog_id = collection_manager.catalogs().get_by_name(catalog).catalog_id()
                installed = collection_manager.get_collection_index().is_installed(
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
            task = self.task_manager().get_task(str(task_id))
            if task is None:
                abort(404, description=f"Task not found with id {task_id}")
            return self.task_manager().get_status(task)

        @self.app.route('/add-catalog')
        def add_catalog():
            url = request.args.get("src")
            catalog = self.album_instance.collection_manager().catalogs().add_by_src(url)
            catalog_id = catalog.catalog_id()
            return {"catalog_id": catalog_id}

        @self.app.route('/remove-catalog')
        def remove_catalog():
            url = request.args.get("src", default=None)
            name = request.args.get("name", default=None)
            if name is None:
                self.album_instance.collection_manager().catalogs().remove_from_collection_by_src(url)
            else:
                self.album_instance.collection_manager().catalogs().remove_from_collection_by_name(name)
            return {}

        @self.app.route('/upgrade')
        def upgrade():
            src = request.args.get("src", default=None)
            name = request.args.get("name", default=None)
            dry_run = request.args.get("dry_run", default=False)
            if name is None and src is None:
                res = self.album_instance.collection_manager().catalogs().update_collection(dry_run=dry_run)
            elif name is None:
                catalog = self.album_instance.collection_manager().catalogs().get_by_src(src)
                res = self.album_instance.collection_manager().catalogs().update_collection(catalog_name=catalog.name(),
                                                                                            dry_run=dry_run)
            else:
                res = self.album_instance.collection_manager().catalogs().update_collection(catalog_name=name,
                                                                                            dry_run=dry_run)
            r = {}
            for catalog_name in res:
                r[catalog_name] = res[catalog_name].as_dict()
            return r

        @self.app.route('/update')
        def update():
            src = request.args.get("src", default=None)
            name = request.args.get("name", default=None)
            if name is None and src is None:
                self.album_instance.collection_manager().catalogs().update_any()
            elif name is None:
                catalog = self.album_instance.collection_manager().catalogs().get_by_src(src)
                self.album_instance.collection_manager().catalogs().update_any(catalog.name())
            else:
                self.album_instance.collection_manager().catalogs().update_any(name)
            return {}

        @self.app.route('/search/<keywords>')
        def search(keywords):
            return self.album_instance.search_manager().search(keywords)

        @self.app.route('/shutdown', methods=['GET'])
        def shutdown():
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                raise RuntimeError('Not running with the Werkzeug Server')
            func()
            return 'Server shutting down...'

    def task_manager(self) -> ITaskManager:
        return self.album_instance.task_manager()

    def _run_solution_method_async(self, catalog, group_name_version: Coordinates, method, args=None):
        task = Task()
        if catalog is None:
            solution_path = str(group_name_version)
        else:
            solution_path = ":".join([catalog, str(group_name_version)])
        task_args = [solution_path]
        if args:
            for arg in args:
                task_args.append(arg)
        task._args = tuple(task_args)
        task._method = method
        self.task_manager().register_task(task)
        return task

    @staticmethod
    def _get_arguments(args_json):
        command_args = [""]
        if args_json:
            for key in args_json:
                command_args.append(f"--{key}")
                command_args.append(str(args_json[key]))
        return command_args

import json
import sys
import threading

from flask import Flask
from flask import request

from hips.core.concept.singleton import Singleton
from hips.core.controller.catalog_manager import CatalogManager
from hips.core.controller.deploy_manager import DeployManager
from hips.core.controller.install_manager import InstallManager
from hips.core.controller.remove_manager import RemoveManager
from hips.core.controller.run_manager import RunManager
from hips.core.controller.search_manager import SearchManager
from hips.core.controller.test_manager import TestManager
from hips.core.model.catalog_collection import HipsCatalogCollection
from hips_runner import logging

module_logger = logging.get_active_logger


class HipsServer(threading.Thread, metaclass=Singleton):
    running = False
    port = 5476

    # load singletons
    catalog_collection = HipsCatalogCollection()
    hips_catalog_manager = CatalogManager(catalog_collection)
    deploy_manager = DeployManager(catalog_collection)
    install_manager = InstallManager(catalog_collection)
    remove_manager = RemoveManager(catalog_collection)
    run_manager = RunManager(catalog_collection)
    search_manager = SearchManager(catalog_collection)
    test_manager = TestManager(catalog_collection)

    def __init__(self, port):
        self.port = port

        threading.Thread.__init__(self)

    def start(self):
        # Start the thread.
        print('Starting HIPS server thread')
        self.running = True
        self.daemon = False
        threading.Thread.start(self)

    def stop(self):
        # Stop the thread.
        print('Stopping HIPS server thread')
        self.running = False
        print('Done stopping HIPS server thread')

    def run(self):
        # Setup the network socket.
        # print(f"HIPS Server listening on {HOST}:{self.port}")
        app = Flask(__name__)

        @app.route("/")
        def hello_world():
            return {"message": "Hello World"}

        @app.route("/config")
        def get_config():
            return {
                "hips_config_path": str(self.catalog_collection.config_file_path),
                "hips_config": self.catalog_collection.config_file_dict,
                "cache_base": str(self.catalog_collection.configuration.base_cache_path),
                "cache_catalogs": str(self.catalog_collection.configuration.cache_path_solution),
                "cache_apps": str(self.catalog_collection.configuration.cache_path_app),
                "cache_downloads": str(self.catalog_collection.configuration.cache_path_download)
            }

        @app.route("/index")
        def get_index():
            return self.catalog_collection.get_search_index()

        @app.route('/<catalog>/<group>/<name>/<version>/run')
        def run(catalog, group, name, version):
            args_json = request.get_json()
            threading.Thread(target=self.__run_hips_command, args=[catalog, group, name, version, "run", args_json],
                             daemon=False).start()
            return {}

        @app.route('/<catalog>/<group>/<name>/<version>/install')
        def install(catalog, group, name, version):
            args_json = request.get_json()
            threading.Thread(target=self.__run_hips_command, args=[catalog, group, name, version, "install", args_json],
                             daemon=False).start()
            return {}

        @app.route('/shutdown', methods=['GET'])
        def shutdown():
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                raise RuntimeError('Not running with the Werkzeug Server')
            func()
            return 'Server shutting down...'

        app.run(port=self.port)

    def __run_hips_thread(self, hips_path, command, command_args):
        sys.argv = str(command_args).split(" ")
        if command == "install":
            InstallManager().install(hips_path)
        if command == "run":
            RunManager().run(hips_path)

    def __run_hips_command(self, catalog, group, name, version, command, args_json):
        args = ""
        if args_json:
            request_data = json.loads(args_json)
            for key in request_data:
                args += f"--{key}={str(request_data[key])} "
        module_logger().info(args)
        solution = self.catalog_collection.resolve_directly(catalog_id=catalog, group=group, name=name,
                                                            version=version)
        if solution is None:
            module_logger().error(f"Solution not found: {catalog}:{group}:{name}:{version}")
            return
        hips_path = str(solution['path'])
        command_args = str(hips_path)
        for arg in args:
            command_args += f" --{arg} {getattr(args, arg)}"
        module_logger().info("launching " + command_args)
        # FIXME this should run in a thread, but produces a PicklingError on Windows
        # Process(target=self.__run_hips_thread, args=(hips_path, command, command_args)).start()
        self.__run_hips_thread(hips_path, command, command_args)

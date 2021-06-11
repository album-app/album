import json
import threading

from flask import Flask
from flask import request

from hips.core.concept.singleton import Singleton
from hips.core.model.catalog_configuration import HipsCatalogCollection
from hips.core.utils import subcommand


class HipsServer(threading.Thread, metaclass=Singleton):
    running = False
    port = 5476
    catalog_configuration = None

    def __init__(self, port):

        self.catalog_configuration = HipsCatalogCollection()
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
                "hips_config_path": str(self.catalog_configuration.config_file_path),
                "hips_config": self.catalog_configuration.config_file_dict,
                "cache_base": str(self.catalog_configuration.configuration.base_cache_path),
                "cache_catalogs": str(self.catalog_configuration.configuration.cache_path_solution),
                "cache_apps": str(self.catalog_configuration.configuration.cache_path_app),
                "cache_downloads": str(self.catalog_configuration.configuration.cache_path_download)
            }

        @app.route("/index")
        def get_index():
            return self.catalog_configuration.get_search_index()

        @app.route('/<catalog>/<group>/<name>/<version>/run')
        def run(catalog, group, name, version):
            args_json = request.get_json()
            threading.Thread(target=self.__launch_hips, args=[catalog, group, name, version, args_json], daemon=False).start()
            return {}

        @app.route('/shutdown', methods=['GET'])
        def shutdown():
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                raise RuntimeError('Not running with the Werkzeug Server')
            func()
            return 'Server shutting down...'

        app.run(port=self.port)

    def __launch_hips(self, catalog, group, name, version, args_json):
        args = ""
        if args_json:
            request_data = json.loads(args_json)
            for key in request_data:
                args += f"--{key}={str(request_data[key])} "
        print(args)
        hips_path = str(self.catalog_configuration.resolve_directly(
            catalog_id=catalog,
            group=group,
            name=name,
            version=version
        )['path'])
        command_args = ["hips", "run", hips_path]
        for arg in args:
            command_args.append(f"--{arg}")
            command_args.append(f"{args[arg]}")
        print("launching " + str(command_args))
        subcommand.run(command_args)





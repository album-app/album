import os
import threading
from pathlib import Path

from album import core as album
from album.api import install_helper
from album.core.model.configuration import Configuration
from album.core.utils import subcommand

# todo: i am not working anymore. replace me

path_download_macos = "https://download.blender.org/release/Blender2.83/blender-2.83.13-macOS.dmg"
path_download_linux = "https://download.blender.org/release/Blender2.83/blender-2.83.13-linux64.tar.xz"
path_download_windows = "https://download.blender.org/release/Blender2.83/blender-2.83.13-windows64.zip"
download_name_linux = "blender-2.83.13-linux64.tar.gz"
path_run_linux = "blender-2.83.13-linux64/blender"


def install():
    __install_linux()


def __install_linux():
    configuration = Configuration()
    active_solution = album.get_active_solution()
    download_path = install_helper.download_if_not_exists(active_solution, path_download_linux, download_name_linux)
    app_path = configuration.get_cache_path_app(active_solution)
    install_helper.extract_tar(download_path, app_path)


def run_with_server():
    __run_linux()
    return True


def __run_linux():
    configuration = Configuration()
    active_solution = album.get_active_solution()
    blender_path = f"{configuration.get_cache_path_app(active_solution)}/{path_run_linux}"
    dir_path = os.path.dirname(os.path.realpath(__file__))
    threading.Thread(target=lambda blender_path, dir_path: {
        subcommand.run([blender_path, "--python", str(Path(dir_path).joinpath("server.py"))])
    }, args=(blender_path, dir_path), daemon=True).start()


def run_as_client(script, *params):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    args = ["python", str(Path(dir_path).joinpath("client.py")), script]
    args.extend(params)
    subcommand.run(args)

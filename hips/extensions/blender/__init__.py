import os
import threading
from pathlib import Path

import hips
from hips import api
from hips_utils import subcommand

path_download_macos = "https://download.blender.org/release/Blender2.83/blender-2.83.13-macOS.dmg"
path_download_linux = "https://download.blender.org/release/Blender2.83/blender-2.83.13-linux64.tar.xz"
path_download_windows = "https://download.blender.org/release/Blender2.83/blender-2.83.13-windows64.zip"
download_name_linux = "blender-2.83.13-linux64.tar.gz"
path_run_linux = "blender-2.83.13-linux64/blender"


def install():
    __install_linux()


def __install_linux():
    active_hips = hips.get_active_hips()
    download_path = api.download_if_not_exists(active_hips, path_download_linux, download_name_linux)
    app_path = api.get_cache_path_app(active_hips)
    api.extract_tar(download_path, app_path)


def run_with_server():
    __run_linux()
    return True


def __run_linux():
    active_hips = hips.get_active_hips()
    blender_path = f"{api.get_cache_path_app(active_hips)}/{path_run_linux}"
    dir_path = os.path.dirname(os.path.realpath(__file__))
    threading.Thread(target=lambda blender_path, dir_path: {
        subcommand.run([blender_path, "--python", str(Path(dir_path).joinpath("server.py"))])
    }, args=(blender_path, dir_path), daemon=True).start()


def run_as_client(script, *params):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    args = ["python", str(Path(dir_path).joinpath("client.py")), script]
    args.extend(params)
    subcommand.run(args)

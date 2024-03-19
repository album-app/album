import platform
import tarfile
import zipfile

import requests
from album.runner import album_logging
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from album.core.controller.conda_manager import CondaManager

module_logger = album_logging.get_active_logger

import os
import subprocess
import sys
from pathlib import Path

from album.core.api.model.configuration import IConfiguration
from album.core.model.default_values import DefaultValues
from album.core.model.link import Link
from album.core.utils.operations.file_operations import (
    construct_cache_link_target,
)


# TODO: Still has the conda executable of the CondaManager parent class. I don' like that, maybe create an extra package
#  manager class from which every Manager(conda/mamba/micromamba) inherits
def is_downloadable(url):
    """Shows if url is a downloadable resource."""
    with _get_session() as s:
        h = s.head(url, allow_redirects=True)
        header = h.headers
        content_type = header.get("content-type")
        if "html" in content_type.lower():
            return False
        return True


def _get_session():
    s = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)

    adapter = HTTPAdapter(max_retries=retry)

    s.mount("http://", adapter)
    s.mount("https://", adapter)

    return s


def _request_get(url):
    """Get a response from a request to a resource url."""
    with _get_session() as s:
        r = s.get(url, allow_redirects=True, stream=True)

        if r.status_code != 200:
            raise ConnectionError("Could not connect to resource %s!" % url)

        return r


def download_resource(url, path):
    """Downloads a resource given its url."""
    path = Path(path)

    if not is_downloadable(url):
        raise AssertionError('Resource "%s" not downloadable!' % url)

    r = _request_get(url)
    with open(path, "wb") as f:
        for chunk in r:
            f.write(chunk)

    return path


def check_architecture():
    """checks the processor architecture of the system"""
    check = subprocess.run(["uname", "-m"], capture_output=True)
    return check.stdout.decode().rstrip()


def _download_mamba(mamba_base_path):
    """downloads micromamba"""
    if platform.system() == "Windows":
        return _download_mamba_win(Path(mamba_base_path).joinpath("micromamba.zip"))
    elif platform.system() == "Darwin":
        return _download_mamba_macos(Path(mamba_base_path).joinpath("micromamba.tar"))
    elif platform.system() == "Linux":
        return _download_mamba_linux(Path(mamba_base_path).joinpath("micromamba.tar"))
    else:
        raise NotImplementedError("Your operating system is currently not supported.")


def _download_mamba_win(mamba_installer_path):
    """downloads micromamba for windows"""
    return download_resource(
        DefaultValues.micromamba_url_windows.value, mamba_installer_path
    )


def _download_mamba_macos(mamba_installer_path):
    """downloads micromamba for macOS depending on the processor architecture"""
    if check_architecture().__eq__("x86_64"):
        return download_resource(
            DefaultValues.micromamba_url_osx_X86_64.value, mamba_installer_path
        )
    elif check_architecture().lower().__eq__("arm64"):
        return download_resource(
            DefaultValues.micromamba_url_osx_ARM64.value, mamba_installer_path
        )
    else:
        raise NotImplementedError(
            "There is no micromamba version for your processor architecture."
        )


def _download_mamba_linux(mamba_installer_path):
    """downloads micromamba for linux depending on the processor architecture"""
    if check_architecture().__eq__("x86_64"):
        return download_resource(
            DefaultValues.micromamba_url_linux_X86_64.value, mamba_installer_path
        )
    elif check_architecture().lower().__eq__("arm64"):
        return download_resource(
            DefaultValues.micromamba_url_linux_ARM64.value, mamba_installer_path
        )
    elif check_architecture().lower().__eq__("power"):
        return download_resource(
            DefaultValues.micromamba_url_linux_POWER.value, mamba_installer_path
        )
    else:
        raise NotImplementedError(
            "There is no micromamba version for your processor architecture."
        )


def _unpack_mamba_win(mamba_installer, mamba_base_path):
    """unpacks the windows version of the micromamba archive"""
    with zipfile.ZipFile(Path(mamba_installer)) as zip:
        zip.extractall(Path(mamba_base_path))


def _unpack_mamba_unix(mamba_installer, mamba_base_path):
    """unpacks the micromamba archives for linux and macOS"""
    with tarfile.open(mamba_installer, "r") as tar:
        tar.extractall(mamba_base_path)


def _set_mamba_env_vars(mamba_base_path):
    """Sets the micromamba environment variables"""
    os.environ["MAMBA_ROOT_PREFIX"] = str(mamba_base_path)
    os.environ["MAMBA_EXE"] = str(get_mamba_exe(mamba_base_path))


def get_mamba_exe(mamba_base_path) -> str:
    """returns the path to the micromamba executable"""
    if platform.system() == "Windows":
        return str(Path(mamba_base_path).joinpath("Library", "bin", "micromamba.exe"))
    else:
        return str(Path(mamba_base_path).joinpath("bin", "micromamba"))


def install_mamba(album_base_path, mamba_base_path):
    """installs micormamba"""
    if not Path(album_base_path).exists():
        Path(album_base_path).mkdir()
    if not Path(mamba_base_path).exists():
        Path(mamba_base_path).mkdir()

    installer = _download_mamba(mamba_base_path)
    if platform.system() == "Windows":
        _unpack_mamba_win(installer, mamba_base_path)
    else:
        _unpack_mamba_unix(installer, mamba_base_path)
    _set_mamba_env_vars(mamba_base_path)


class MicromambaManager(CondaManager):
    """Class for handling micromamba environments.

    The micromamba class manages the environments a solution is supposed to run in. It provides all features necessary
    for environment creation, deletion, dependency installation, etc.

    Notes:
        An installed \"micromamba\" program must be available and callable at the .album/micromamba directory.

    """

    def __init__(self, configuration: IConfiguration):
        self._micromamba_base_path = configuration.micromamba_base_path()
        self._micromamba_executable = get_mamba_exe(self._micromamba_base_path)
        super().__init__(configuration, self._micromamba_executable)

    @staticmethod
    def check_for_executable():
        if Path(DefaultValues.micromamba_path.value).is_file():
            return True
        else:
            return False

    def _get_install_environment_executable(self):
        return self._micromamba_executable

    def get_active_environment_name(self):
        """Returns the environment from the active album."""
        environment_info = self.get_info()
        env_name = environment_info["environment"]
        env_name = env_name.rstrip(" (active)")
        return env_name

    def get_active_environment_path(self):
        """Returns the environment for the active album."""
        environment_info = self.get_info()
        path = environment_info["env location"]
        link = construct_cache_link_target(
            self._configuration.lnk_path(),
            point_from=path,
            point_to=DefaultValues.lnk_env_prefix.value,
            create=False,
        )
        if link:
            return link
        else:
            return Link(path)

    def _get_env_create_args(self, env_file, env_prefix):
        subprocess_args = [
            self._get_install_environment_executable(),
            "create",
            "-y",
            "--file",
            env_file.name,
            "-p",
            env_prefix,
        ]
        return subprocess_args

    def _get_run_script_args(self, environment_path, script_full_path):
        if sys.platform == "win32" or sys.platform == "cygwin":
            # NOTE: WHEN USING 'CONDA RUN' THE CORRECT ENVIRONMENT GETS TEMPORARY ACTIVATED,
            # BUT THE PATH POINTS TO THE WRONG PYTHON (conda base folder python) BECAUSE THE CONDA BASE PATH
            # COMES FIRST IN ENVIRONMENT VARIABLE "%PATH%". THUS, FULL PATH IS NECESSARY TO CALL
            # THE CORRECT PYTHON OR PIP! ToDo: keep track of this!
            subprocess_args = [
                self._micromamba_executable,
                "run",
                "--prefix",
                os.path.normpath(environment_path),
                os.path.normpath(Path(environment_path).joinpath("python")),
                os.path.normpath(script_full_path),
            ]
        else:
            subprocess_args = [
                self._micromamba_executable,
                "run",
                "--prefix",
                os.path.normpath(environment_path),
                "python",
                "-u",
                os.path.normpath(script_full_path),
            ]
        return subprocess_args

    def _get_remove_env_args(self, path):
        subprocess_args = [
            self._get_install_environment_executable(),
            "remove",
            "-y",
            "-q",
            "-p",
            os.path.normpath(path),
            "--all",
        ]
        return subprocess_args

    def install_if_missing(self):
        micromamba_executable = Path(get_mamba_exe(self._micromamba_base_path))
        if not micromamba_executable.exists():
            install_mamba(
                self._configuration.base_cache_path(), self._micromamba_base_path
            )

    def set_environment_variables(self):
        _set_mamba_env_vars(self._micromamba_base_path)

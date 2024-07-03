"""File operations module."""
import json
import os
import platform
import random
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from album.environments.utils.file_operations import (
    copy,
    copy_folder,
    create_path_recursively,
    force_remove,
)
from album.runner import album_logging

module_logger = album_logging.get_active_logger
enc = sys.getfilesystemencoding()

win_shell = None


def get_dict_entry(
    d: Dict[str, Any], key: str, allow_none: bool = True, message: str = ""
):
    """Receive an entry from a dictionary.

    Args:
        d:
            The yml dictionary.
        key:
            The key.
        allow_none:
            boolean flag indicating whether to allow key to exist or not.
        message:
            When allow_none false this is the message printed in the exception.


    Returns:
        The value or None

    Raises:
        KeyError if allow_none is False and key not found.

    """
    try:
        val = d[key]
    except KeyError:
        val = None
        if not allow_none:
            raise KeyError(message)

    return val


def write_dict_to_json(
    json_file: Union[str, Path], d: Union[Dict[str, Any], List[str]]
) -> bool:
    """Write dictionary to JSON file."""
    json_file = Path(json_file)
    create_path_recursively(json_file.parent)

    with open(json_file, "w+") as json_f:
        json_f.write(json.dumps(d))

    return True


def get_dict_from_json(json_file: Union[str, Path]) -> Dict[str, Any]:
    """Read dictionary from JSON file."""
    json_file = Path(json_file)

    with open(json_file) as json_f:
        d = json.load(json_f)

    return d


def folder_empty(path: Union[str, Path]) -> bool:
    """Return true when a given folder is empty else false."""
    path = Path(path)

    if path.exists():
        if path.is_dir() and os.listdir(path) == []:
            return True
        return False
    return True


def list_files_recursively(
    path: Union[str, Path], root: Union[str, Path] = "", relative: bool = False
) -> List[Path]:
    """List all files in a repository recursively."""
    path = Path(path)
    if not root:
        root = path
    files_list = []

    for cur_root, dirs, files in os.walk(path):
        cur_root_ = Path(cur_root)

        for d in dirs:
            files_list += list_files_recursively(cur_root_.joinpath(d), root, relative)
        for fi in files:
            if relative:
                files_list.append(cur_root_.joinpath(fi).relative_to(root))
            else:
                files_list.append(cur_root_.joinpath(fi))
        break

    return files_list


def create_empty_file_recursively(path_to_file: Union[str, Path]) -> bool:
    """Create an empty file, including missing parent folders."""
    p = Path(path_to_file)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch(exist_ok=True)

    return True


def create_paths_recursively(paths: List[Union[str, Path]]) -> None:
    """Create paths, includes creating missing parent folders."""
    for p in paths:
        create_path_recursively(p)


def copy_in_file(file_content: str, file_path: Union[str, Path]) -> Path:
    """Copy a stream content to a file."""
    file_path = Path(file_path)
    create_path_recursively(file_path.parent)
    if file_path.is_file():
        file_path.unlink()
    with open(file_path, "w") as script_file:
        script_file.write(file_content)
    return file_path


def zip_folder(
    folder_path: Union[str, Path], zip_archive_file: Union[str, Path]
) -> str:
    """Create a zip archive of a given folder."""
    zip_archive_file = Path(zip_archive_file)

    if zip_archive_file.suffix == ".zip":  # remove suffix as it appends automatically
        zip_archive_file = zip_archive_file.with_suffix("")

    create_path_recursively(zip_archive_file.parent)

    return shutil.make_archive(str(zip_archive_file), "zip", folder_path)


def zip_paths(
    paths_to_include: List[Union[str, Path]],
    zip_archive_file: Union[str, Path],
    tmp_dir: Union[str, Path, None] = None,
) -> str:
    """Create a zip archive including all given files. Copies the data into a tmp directory first."""
    with tempfile.TemporaryDirectory(dir=tmp_dir) as tmp_folder:
        for file in paths_to_include:
            file = Path(file)
            if file.is_file():
                copy(file, tmp_folder)
            elif file.is_dir():
                copy_folder(file, tmp_folder)
            else:
                raise FileNotFoundError("Could not find file %s" % str(file))

        return zip_folder(tmp_folder, zip_archive_file)


def unzip_archive(
    zip_archive_file: Union[str, Path], target_folder: Union[str, Path] = ""
) -> Path:
    """Unzip an archive file to a given folder or the folder where it is located (default)."""
    zip_archive_file = Path(zip_archive_file)
    target_folder = Path(target_folder) if target_folder else zip_archive_file.parent

    create_path_recursively(target_folder)

    shutil.unpack_archive(str(zip_archive_file), str(target_folder))

    return target_folder


def remove_link(link_target: Path) -> None:
    """Remove a link from the file system."""
    if link_target:
        dispose_op = getattr(link_target, "dispose", None)
        if callable(dispose_op):
            dispose_op()
        else:
            raise RuntimeError("Path doesn't seem to be a link")
        force_remove(link_target)


def rand_folder_name(f_len: int = 8) -> str:
    """Create random folder name of length given."""
    characters = "abcdefghijklmnopqrstuvwxyz0123456789_"
    s = []
    for _ in range(0, f_len):
        s.append(characters[random.randint(0, len(characters) - 1)])
    return "".join(s)


def check_zip(path: Union[Path, str]) -> bool:
    """Check a given zip file."""
    return zipfile.is_zipfile(path)


def construct_cache_link_target(
    point_to_base: Path, point_from: Path, point_to: Path, create: bool = True
) -> Optional[Path]:
    """Construct a link from point_from to point_to.

    Args:
        point_to_base:
            Base folder where to point to.
        point_from:
            Path where to point from.
        point_to:
            Folder name in point_to_base where to point to.
        create:
            Flag indicating whether to create the link.

    Returns:
        Path to the resolved link.

    """
    operation_system = platform.system().lower()
    root = point_to_base.joinpath(point_to)

    if "windows" in operation_system:
        point_from_ = str(point_from) + ".lnk"
        shortcut = Path(point_from_)
        if shortcut.exists():
            return _get_shortcut_target(shortcut)
        if create:
            point_to = root.joinpath(_next_free_pointer_number(root))

            create_path_recursively(point_to)
            create_path_recursively(shortcut.parent)

            _create_shortcut(shortcut, target=point_to)
            resolve = point_to.absolute()
            return resolve
    else:
        if os.path.islink(point_from):
            r = Path(point_from).resolve()

            if not r.exists():
                create_path_recursively(r)

            return r
        if create:
            point_to = root.joinpath(_next_free_pointer_number(root))

            create_path_recursively(point_to)
            create_path_recursively(Path(point_from).parent)

            # point_from -> point_to
            os.symlink(str(point_to), point_from, target_is_directory=True)
            return point_to.resolve()

    return Path("")


def _next_free_pointer_number(root: Union[str, Path]) -> str:
    """Determine the next free point_to number."""
    root = Path(root)

    # determine next free point_to number
    i = 0
    while root.joinpath("%s" % i).exists():
        i += 1

    return str(i)


def get_link_target(link: Union[str, Path]) -> Optional[Path]:
    """Return the target of a link."""
    operation_system = platform.system().lower()
    if "windows" in operation_system:
        # pylnk3 is windows only
        link_ = str(link) + ".lnk"
        shortcut = Path(link_)
        if shortcut.exists():
            return _get_shortcut_target(shortcut)
    else:
        if Path(link).exists():
            return Path(link).resolve()
    return None


def _create_shortcut(shortcut_path: Union[str, Path], target: Union[str, Path]) -> None:
    """Create a shortcut to a given target."""
    shortcut_path = Path(shortcut_path)
    if not shortcut_path.parent.exists():
        shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    sh = _get_global_win_shell()
    wscript = sh.CreateShortCut(str(shortcut_path.absolute()))
    wscript.TargetPath = str(Path(target).absolute())
    wscript.save()


def _get_shortcut_target(shortcut_path: Union[str, Path]) -> Path:
    """Get the target of a shortcut."""
    shortcut_path = Path(shortcut_path)
    if not shortcut_path.parent.exists():
        raise LookupError("Shortcut %s doesn't exist." % shortcut_path)

    sh = _get_global_win_shell()
    wscript = sh.CreateShortCut(str(shortcut_path.absolute()))
    return Path(wscript.TargetPath)


def _get_global_win_shell() -> Any:
    """Get the global windows shell."""
    global win_shell
    import win32com.client

    if win_shell is None:
        win_shell = win32com.client.Dispatch("Wscript.Shell")
    return win_shell

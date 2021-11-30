import errno
import json
import os
import random
import re
import shutil
import stat
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

import yaml

from album.runner import album_logging

module_logger = album_logging.get_active_logger
enc = sys.getfilesystemencoding()


def get_line_indent(line):
    """Returns the line indent of a line."""
    return int(len(re.findall('^[ ]*', line)[0]) / 4)


def indent_to_space(indent: int):
    """Returns the right number of spaces belonging to an indent"""
    return ''.join([' '] * 4 * indent)


def is_comment(line):
    """Finds out if line is a comment line."""
    if re.match('^[ ]*[#]', line):
        return True
    return False


def is_blank_line(line):
    """Finds out if line is blank."""
    if re.match('^\n', line):
        return True
    return False


def to_executable(argument_parsing):
    """Connects all arguments in a argument list"""
    executable = ""
    for arg in argument_parsing:
        executable += arg
    return executable


def get_dict_from_yml(yml_file):
    """Reads a dictionary from a file in yml format."""
    with open(yml_file, 'r') as yml_f:
        d = yaml.safe_load(yml_f)

    if not isinstance(d, dict):
        raise TypeError("Yaml file %s invalid!" % str(yml_file))

    return d


def write_dict_to_yml(yml_file, d):
    """Writes a dictionary to a file in yml format."""
    yml_file = Path(yml_file)
    create_path_recursively(yml_file.parent)

    with open(yml_file, 'w+') as yml_f:
        yml_f.write(yaml.dump(d, Dumper=yaml.Dumper))

    return True


def get_dict_entry(d, key, allow_none=True, message=None):
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


def write_dict_to_json(json_file, d):
    """Writes dictionary to JSON file."""
    json_file = Path(json_file)
    create_path_recursively(json_file.parent)

    with open(json_file, 'w+') as json_f:
        json_f.write(json.dumps(d))

    return True


def get_dict_from_json(json_file):
    """Reads dictionary from JSON file."""
    json_file = Path(json_file)

    with open(json_file, 'r') as json_f:
        d = json.load(json_f)

    return d


def folder_empty(path) -> bool:
    path = Path(path)

    if path.exists():
        if path.is_dir() and os.listdir(path) == []:
            return True
        return False
    return True


def create_empty_file_recursively(path_to_file):
    """Creates an empty file. Creates missing parent folders."""
    p = Path(path_to_file)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch(exist_ok=True)

    return True


def create_path_recursively(path):
    """Creates a path. Creates missing parent folders."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)

    return True


def create_paths_recursively(paths):
    """Create paths. Creates missing parent folders."""
    for p in paths:
        create_path_recursively(p)


def copy_folder(folder_to_copy, destination, copy_root_folder=True, force_copy=False):
    folder_to_copy = Path(folder_to_copy)
    destination = Path(destination)

    if os.path.exists(destination) and os.path.samefile(folder_to_copy, destination):
        return destination

    if copy_root_folder:
        destination = destination.joinpath(folder_to_copy.name)

    if force_copy:
        force_remove(destination)

    create_path_recursively(destination)

    for root, dirs, files in os.walk(folder_to_copy):
        root = Path(root)

        for d in dirs:
            copy_folder(root.joinpath(d), destination.joinpath(d), copy_root_folder=False)
        for fi in files:
            copy(root.joinpath(fi), destination)
        break

    return destination


def copy(file, path_to) -> Path:
    """Copies a file A to either folder B or file B. Makes sure folder structure for target exists."""
    file = Path(file)
    path_to = Path(path_to)

    if os.path.exists(path_to) and os.path.samefile(file, path_to):
        return path_to

    create_path_recursively(path_to.parent)

    return Path(shutil.copy(file, path_to))


def copy_in_file(file_content, file_path) -> Path:
    """Copies a stream content to a file."""
    file_path = Path(file_path)
    create_path_recursively(file_path.parent)
    if file_path.is_file():
        file_path.unlink()
    with open(file_path, "w") as script_file:
        script_file.write(file_content)
    return file_path


def zip_folder(folder_path, zip_archive_file):
    """Creates a zip archive of a given folder."""
    zip_archive_file = Path(zip_archive_file)

    if zip_archive_file.suffix == ".zip":  # remove suffix as it appends automatically
        zip_archive_file = zip_archive_file.with_suffix("")

    create_path_recursively(zip_archive_file.parent)

    return shutil.make_archive(str(zip_archive_file), 'zip', folder_path)


def zip_paths(paths_to_include, zip_archive_file):
    """Creates a zip archive including all given files. Copies the data into a tmp directory first."""

    with tempfile.TemporaryDirectory() as tmp_folder:
        for file in paths_to_include:
            file = Path(file)
            if file.is_file():
                copy(file, tmp_folder)
            elif file.is_dir():
                copy_folder(file, tmp_folder)
            else:
                raise FileNotFoundError("Could not find file %s" % str(file))

        return zip_folder(tmp_folder, zip_archive_file)


def unzip_archive(zip_archive_file, target_folder=None):
    """Unzips a archive file to a given folder or the folder where it is located (default)."""
    zip_archive_file = Path(zip_archive_file)
    target_folder = Path(target_folder) if target_folder else zip_archive_file.parent

    create_path_recursively(target_folder)

    shutil.unpack_archive(str(zip_archive_file), str(target_folder))

    return target_folder


def force_remove(path, warning=True):
    path = Path(path)
    if path.exists():
        try:
            if path.is_file():
                try:
                    path.unlink()
                except PermissionError:
                    handle_remove_readonly(os.unlink, path, sys.exc_info())
            else:
                shutil.rmtree(path, ignore_errors=False, onerror=handle_remove_readonly)
        except PermissionError as e:
            module_logger().warn("Cannot delete %s." % str(path))
            if not warning:
                raise e


def handle_remove_readonly(func, path, exc):
    excvalue = exc[1]
    if func in (os.rmdir, os.remove, os.unlink) and excvalue.errno == errno.EACCES:
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777
        func(path)
    else:
        raise


def rand_folder_name(f_len=8):
    characters = "abcdefghijklmnopqrstuvwxyz0123456789_"
    s = []
    for i in range(0, f_len):
        s.append(characters[random.randint(0, len(characters) - 1)])
    return "".join(s)


def check_zip(path):
    return not ZipFile(path).testzip()

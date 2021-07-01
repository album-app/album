import json
import os
import re
import shutil
import subprocess
import zipfile
import tempfile
import sys
import time
from pathlib import Path
from hips.core.utils.subcommand import run
from stat import *

import yaml

from hips.core.model.default_values import HipsDefaultValues
from hips_runner import logging

module_logger = logging.get_active_logger
enc = sys.getfilesystemencoding()


class FileOperationError(Exception):
    """Exception class for argument extraction"""

    def __init__(self, short_message, long_message):
        self.short_message = short_message
        self.long_message = long_message


# def auto_format(file):
#    """Autformats file to pep8 standard."""
#    fixed_file = autopep8.fix_file(file)
#    return fixed_file


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


def extract_argparse(file):
    """Extracts the argument parsing from a python file.

    Args:
        file:
            The file to extract argument parsing from.

    Returns:
        list of all arguments.
    """
    argument_parsing = ["global args\n"]

    # one could think of autoformat stuff to be sure indents are correct - because the following should NOT happen
    # arser.add_argument(\'--mkldnn\', action=\'store_true\', help=\'for
    # mxnet, force MXNET_SUBGRAPH_BACKEND = "MKLDNN"\') <-- wrong indent, but allowed by python parser. Would be fixed
    # with autoformat.

    # string = auto_format(file)

    with open(file, 'r') as f:
        # search for argparse line
        while True:
            line = f.readline()
            if not line:
                break

            # store line indent to begin with
            previous_indent = get_line_indent(line)

            # all lines which follow should belong to argument parsing
            if "argparse.ArgumentParser" in line:
                argument_parsing.append(line.strip() + '\n')
                while True:
                    line = f.readline()
                    if not line:
                        break
                    if ".add_argument(" in line:  # adding argument
                        argument_parsing.append(line.strip() + '\n')
                    elif ".parse_args(" in line:  # end of collecting arguments
                        argument_parsing.append("args = " + line.strip() + '\n')
                        return to_executable(argument_parsing)
                    elif previous_indent < get_line_indent(line):  # linebreak within add_argument command
                        argument_parsing[-1] = argument_parsing[-1][:-1] + line.strip() + '\n'
                        continue
                    elif is_comment(line) or is_blank_line(line):  # blank lines or comments are skipped
                        continue
                    else:  # conditional argument parsing or some logic between two add_argument commands is prohibited
                        raise FileOperationError("Argument parsing went wrong! Illegal sequence of commands. ",
                                                 "Argument parsing went wrong! "
                                                 "Detected line '{}' after ArgumentParser initiation.".format(line))
                    # set new indent
                    previous_indent = get_line_indent(line)
    return ""


def get_zenodo_metadata(file, metadata):
    def extract_metadata(l):
        tmp = l.replace(metadata + "=", "").split("#")[0].strip().replace("\"", "")
        if tmp[-1] == ",":
            tmp = tmp[:-1]

        return tmp

    with open(file, 'r') as f:
        # search for argparse line
        while True:
            line = f.readline()
            if not line:
                break

            # safety feature - no one should simply have "metadata=" written somewhere else!
            if "setup(\n" == line:
                hips_setup_indent = get_line_indent(line)
                while True:
                    line = f.readline()
                    if not line:
                        return None
                    elif hips_setup_indent < get_line_indent(line):  # setup line
                        if line.startswith(indent_to_space(hips_setup_indent + 1) + metadata + "="):
                            deposit_id = extract_metadata(line)
                            return deposit_id
                    elif is_comment(line) or is_blank_line(line):  # blank lines or comments are skipped
                        continue
                    elif hips_setup_indent == get_line_indent(line) and line == ')\n' \
                            or line == indent_to_space(hips_setup_indent + 1) + '})\n':  # hips.setup call finished
                        break
                    else:
                        raise FileOperationError("Retrieving doi failed. ",
                                                 "Retrieving doi failed! File wrongly formatted? "
                                                 "Detected line '{}' after \"setup(\" initiation.".format(line))


def set_zenodo_metadata_in_solutionfile(file, doi, deposit_id):
    module_logger().debug("Set doi %s and deposit_id: %s in file %s..." % (doi, deposit_id, file))

    solution_name, solution_ext = os.path.splitext(os.path.basename(file))
    solution_name_full = solution_name + "_tmp" + solution_ext

    new_file_path = HipsDefaultValues.app_cache_dir.value.joinpath(solution_name_full)
    create_path_recursively(new_file_path.parent)
    new_file = new_file_path.open('w+')

    with open(file, 'r') as f:
        # search for argparse line
        while True:
            line = f.readline()
            new_file.write(line)
            if not line:
                break

            # all lines which follow should belong to setup(
            if "setup(\n" == line:
                hips_setup_indent = get_line_indent(line)

                # add doi
                doi_line = indent_to_space(hips_setup_indent + 1) + "doi=\"%s\",\n" % doi
                new_file.write(doi_line)

                # add deposit_id
                deposit_id_line = indent_to_space(hips_setup_indent + 1) + "deposit_id=\"%s\",\n" % deposit_id
                new_file.write(deposit_id_line)

                # add other lines and delete old doi entry if exists
                while True:
                    line = f.readline()
                    if not line:
                        break
                    elif is_comment(line) or is_blank_line(line):  # blank lines or comments are skipped
                        continue
                    elif hips_setup_indent < get_line_indent(line):  # setup line
                        if line.startswith(indent_to_space(hips_setup_indent + 1) + "doi="):  # old doi
                            continue
                        if line.startswith(indent_to_space(hips_setup_indent + 1) + "deposit_id="):  # old deposit_id
                            continue
                        new_file.write(line)
                    elif hips_setup_indent == get_line_indent(line) and line == ')\n' \
                            or line == indent_to_space(hips_setup_indent + 1) + '})\n':  # hips.setup call finished
                        new_file.write(line)
                        break
                    else:
                        new_file.close()
                        os.remove(str(new_file_path))
                        raise FileOperationError("Writing doi failed. ",
                                                 "Writing doi failed! File wrongly formatted? "
                                                 "Detected line '{}' after \"setup(\" initiation.".format(line))

    new_file.close()

    shutil.copy(str(new_file_path), file)

    return file


def get_dict_from_yml(yml_file):
    """Reads a dictionary from a file in yml format."""
    with open(yml_file, 'r') as yml_f:
        d = yaml.safe_load(yml_f)

    return d


def write_dict_to_yml(yml_file, d):
    """Writes a dictionary to a file in yml format."""
    yml_file = Path(yml_file)
    create_path_recursively(yml_file.parent)

    with open(yml_file, 'w+') as yml_f:
        yml_f.write(yaml.dump(d, Dumper=yaml.Dumper))

    return True


def get_yml_entry(d, key, allow_none=True):
    """Receive an entry from a dictionary.

    Args:
        d:
            The yml dictionary.
        key:
            The key.
        allow_none:
            boolean flag indicating whether to allow key to exist or not.

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
            raise

    return val


def write_dict_to_json(json_file, d):
    """Writes dictionary to JSON file."""
    json_file = Path(json_file)
    create_path_recursively(json_file.parent)

    with open(json_file, 'w+') as json_f:
        json_f.write(json.dumps(d))

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


def copy_folder(folder_to_copy, destination, copy_root_folder=True):
    folder_to_copy = Path(folder_to_copy)
    destination = Path(destination)

    if copy_root_folder:
        destination = destination.joinpath(folder_to_copy.name)

    create_path_recursively(destination)

    for root, dirs, files in os.walk(folder_to_copy):
        root = Path(root)

        for d in dirs:
            copy_folder(root.joinpath(d), destination.joinpath(d), copy_root_folder=False)
        for fi in files:
            copy(root.joinpath(fi), destination)


def copy(file, path_to):
    """Copies a file A to either folder B or file B. Makes sure folder structure for target exists."""
    file = Path(file)
    path_to = Path(path_to)
    create_path_recursively(path_to.parent)

    return shutil.copy(file, path_to)


def copy_in_file(file_content, file_path):
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

    return shutil.make_archive(zip_archive_file, 'zip', folder_path)


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

        zip_folder(tmp_folder, zip_archive_file)


def unzip_archive(zip_archive_file, target_folder=None):
    """Unzips a archive file to a given folder or the folder where it is located (default)."""
    zip_archive_file = Path(zip_archive_file)
    target_folder = Path(target_folder) if target_folder else zip_archive_file.parent

    create_path_recursively(target_folder)

    shutil.unpack_archive(str(zip_archive_file), str(target_folder))

    return target_folder


def remove_warning_on_error(path):
    global brute_force
    brute_force = False

    def handle_error(f, p_file, __):
        if sys.platform == 'win32' or sys.platform == 'cygwin':
            global brute_force
            brute_force = True
        else:
            os.chmod(path, S_IWRITE | S_IREAD | S_IEXEC)
            for root, dirs, files in os.walk(path):
                root = Path(root)
                for d in dirs:
                    os.chmod(root.joinpath(d), S_IWRITE | S_IREAD | S_IEXEC)
                for fi in files:
                    os.chmod(root.joinpath(fi), S_IWRITE | S_IREAD | S_IEXEC)
            f(p_file)  # call the calling function again on the failing file

    path = Path(path)
    if path.exists():
        try:
            shutil.rmtree(path, onerror=handle_error)
        except FileNotFoundError as e:
            module_logger().warning("Could not remove %s! Reason: %s" % (str(path), e.strerror))
        except PermissionError as e:
            module_logger().warning("Could not remove %s! Reason: %s" % (str(path), e.strerror))
        finally:
            if brute_force:  # windows only
                module_logger().debug("Trying brute force removal...")
                cmd = 'cmd.exe /C del /f /s /q \"%s\"' % str(path)
                try:
                    run(cmd, timeout1=60, timeout2=6000)

                    try:
                        i = 0
                        while path.exists() and i < 10:
                            i += 1
                            time.sleep(1)
                    except PermissionError:
                        time.sleep(1)
                        pass
                except RuntimeError:
                    module_logger().warning("Could not remove %s with brute force!" % str(path))
                else:
                    module_logger().info("Brute force successfully removed %s!" % str(path))
    else:
        module_logger().info("No content in %s! Nothing to delete..." % str(path))

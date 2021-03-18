import os
import re
import shutil

from xdg import xdg_cache_home

from utils import hips_logging

module_logger = hips_logging.get_active_logger


class FileOperationError(Exception):
    """Exception class for argument extraction"""

    def __init__(self, short_message, long_message):
        self.short_message = short_message
        self.long_message = long_message


def get_line_indent(line):
    """Returns the line indent of a line."""
    return int(len(re.findall('^[ ]*', line)[0])/4)


def indent_to_space(indent: int):
    """Returns the right number of spaces belonging to an indent"""
    return ''.join([' ']*4*indent)


#def auto_format(file):
#    """Autformats file to pep8 standard."""
#    fixed_file = autopep8.fix_file(file)
#    return fixed_file


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
            if "hips.setup(\n" == line:
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
                    elif hips_setup_indent == get_line_indent(line) and line == ')\n'\
                            or line == indent_to_space(hips_setup_indent + 1) + '})\n':  # hips.setup call finished
                        break
                    else:
                        raise FileOperationError("Retrieving doi failed. ",
                                                 "Retrieving doi failed! File wrongly formatted? "
                                                 "Detected line '{}' after \"hips.setup(\" initiation.".format(line))


def set_zenodo_metadata_in_solutionfile(file, doi, deposit_id):
    module_logger().debug("Set doi %s and deposit_id: %s in file %s" % (doi, deposit_id, file))

    solution_name, solution_ext = os.path.splitext(os.path.basename(file))
    solution_name_full = solution_name + "_tmp" + solution_ext

    new_file_path = xdg_cache_home().joinpath(solution_name_full)
    new_file = new_file_path.open('w+')

    with open(file, 'r') as f:
        # search for argparse line
        while True:
            line = f.readline()
            new_file.write(line)
            if not line:
                break

            # all lines which follow should belong to hips.setup(
            if "hips.setup(\n" == line:
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
                    elif hips_setup_indent == get_line_indent(line) and line == ')\n'\
                            or line == indent_to_space(hips_setup_indent + 1) + '})\n':  # hips.setup call finished
                        new_file.write(line)
                        break
                    else:
                        new_file.close()
                        os.remove(str(new_file_path))
                        raise FileOperationError("Writing doi failed. ",
                                                 "Writing doi failed! File wrongly formatted? "
                                                 "Detected line '{}' after \"hips.setup(\" initiation.".format(line))

    new_file.close()

    shutil.copy(str(new_file_path), file)

    return file

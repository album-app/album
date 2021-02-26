import re
import autopep8


class ExtractArgparseError(Exception):
    """Exception class for argument extraction"""

    def __init__(self, short_message, long_message):
        self.short_message = short_message
        self.long_message = long_message


def get_line_indent(line):
    """Returns the line indent of a line."""
    return len(re.findall('^[ ]*', line)[0])/4


def auto_format(file):
    """Autformats file to pep8 standard."""
    fixed_file = autopep8.fix_file(file)
    return fixed_file


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
                        raise ExtractArgparseError("Argument parsing went wrong! Illegal sequence of commands. ",
                                                   "Argument parsing went wrong! "
                                                   "Detected line '{}' after ArgumentParser initiation.".format(line))
                    # set new indent
                    previous_indent = get_line_indent(line)
    return ""

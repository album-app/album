import io
import subprocess
import sys

import pexpect

from hips.core.model import logging
from hips.core.model.logging import LogfileBuffer

module_logger = logging.get_active_logger


# todo: class SubcommandRun?

def run(command, log_output=True, message_formatter=None):
    """Runs a command in a subprocess thereby logging its output.

    Args:
        log_output:
            Indicates whether to log the output of the subprocess or not.
        message_formatter:
            Possibility to parse a lambda to format the message in a certain way.
        command:
            The command to run.

    Returns:
        Exit status of the subprocess.

    Raises:
        RuntimeError:
            When exit-status of subprocess is not 0.

    """

    module_logger().info('Running command: %s...' % " ".join(command))
    exit_status = 1

    log = LogfileBuffer(message_formatter)
    if not log_output:
        log = io.StringIO()

    operation_system = sys.platform
    if operation_system != 'win32' or operation_system != 'cygwin':
        (_, exit_status) = pexpect.run(
            " ".join(command), logfile=log, withexitstatus=1, timeout=None, encoding='utf-8'
        )
        if exit_status != 0:
            module_logger().error(log.getvalue())
            raise RuntimeError("Command failed due to reasons above!")
    else:
        process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
        while True:
            if process.poll() is not None:
                break
            output = process.stdout.readline()
            if output and isinstance(log, LogfileBuffer):
                log.write(output)

        out, err = process.communicate()
        if process.returncode:
            raise Exception(
                "Return code: %(ret_code)s Error message: %(err_msg)s"
                % {"ret_code": process.returncode, "err_msg": err}
            )
        if err:
            module_logger().warning(log.getvalue())
            module_logger().warning(
                "An error was caught that is not treated as stop condition for the hips framework: \n"
                "\t %s" % err)
            [x.flush() for x in module_logger().handlers]

            exit_status = process.returncode

    return exit_status

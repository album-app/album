import subprocess
import sys

import pexpect

from hips_utils import hips_logging
from hips_utils.hips_logging import LogfileBuffer

module_logger = hips_logging.get_active_logger


def run(command):
    module_logger().info('Running command: %s' % " ".join(command))
    exit_status = 1

    operation_system = sys.platform
    if operation_system != 'win32' or operation_system != 'cygwin':
        (_, exit_status) = pexpect.run(
         " ".join(command), logfile=LogfileBuffer(), withexitstatus=1, timeout=None, encoding='utf-8'
        )
    else:
        log = LogfileBuffer()
        process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
        while True:
            if process.poll() is not None:
                break
            output = process.stdout.readline()
            if output:
                log.write(output)

        out, err = process.communicate()
        if process.returncode:
            raise Exception(
              "Return code: %(ret_code)s Error message: %(err_msg)s"
              % {"ret_code": process.returncode, "err_msg": err}
              )
        if err:
            module_logger().warning("An error was caught that is not treated as stop condition for the hips framework: \n"
                                    "\t %s" % err)
            [x.flush() for x in module_logger().handlers]

            exit_status = process.returncode

    return exit_status

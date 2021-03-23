import subprocess

from utils import hips_logging

module_logger = hips_logging.get_active_logger


def run(command):
    module_logger().info('Running command: %s' % command)
    process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            # TODO: be smarter about log level based on output line (e.g. catch errors)
            module_logger().info(output.strip())
    out, err = process.communicate()
    if process.returncode:
        raise Exception(
          "Return code: %(ret_code)s Error message: %(err_msg)s"
          % {"ret_code": process.returncode, "err_msg": err}
          )
    return process.returncode, out, err

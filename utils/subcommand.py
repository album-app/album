import subprocess
import shlex
import logging


module_logger = logging.getLogger('hips')


def run(command):
    module_logger.info('Running command: %s' % command)
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, universal_newlines=True)
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            # TODO: be smarter about log level based on output line (e.g. catch errors)
            module_logger.info(output.strip())
    rc = process.poll()
    return rc
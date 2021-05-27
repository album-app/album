import io
import queue
import signal
import subprocess
import sys
import threading
from queue import Queue

import pexpect

from hips.core.model import logging
from hips.core.model.logging import LogfileBuffer

module_logger = logging.get_active_logger


class SaveThreadWithReturn:

    def __init__(self, action, action2=None, timeout=1, timeout2=5):
        if not callable(action):
            raise ValueError("Action needs to be callable!")

        if action2:
            if not callable(action2):
                raise ValueError("Action2 needs to be callable if set!")
        else:
            action2 = self.stop

        self.que = Queue()
        self.action = action
        self.action2 = action2
        self.timeout = timeout
        self.timeout2 = timeout2
        self.errors = False
        self.thread = None
        self.thread_id = -1

    def run(self):
        self.thread = threading.Thread(target=lambda: self.que.put(self.action()))
        self.thread.daemon = True  # important for the main python to be able to finish
        self.thread.start()
        self.thread.join(self.timeout)

        if self.thread.is_alive():
            self.action2()
            self.thread.join(self.timeout2)
            if self.thread.is_alive():
                self._stop_routine()

        r = None

        try:
            r = self.que.get_nowait()
        except queue.Empty:
            self._stop_routine()

        return r

    def _stop_routine(self):
        self.thread_id = self.thread.ident
        self.errors = True
        self.stop()
        return None

    def stop(self):
        if sys.platform == 'win32' or sys.platform == 'cygwin':
            # there is no easy way to send a signal from one thread to another...
            pass
        else:
            signal.pthread_kill(self.thread_id, signal.SIGKILL)


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
    if operation_system == 'linux' or operation_system == 'darwin':
        (_, exit_status) = pexpect.run(
            " ".join(command), logfile=log, withexitstatus=1, timeout=None, encoding='utf-8'
        )
        if exit_status != 0:
            module_logger().error(log.getvalue())
            raise RuntimeError("Command failed due to reasons above!")
    else:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            universal_newlines=True,
            shell=True
        )

        save_communicate = True

        poll = SaveThreadWithReturn(process.poll)
        read_message = SaveThreadWithReturn(
            process.stdout.readline,
            lambda: process.stdin.write("\r\n"),  # after 60 seconds of no feedback try to send a linebreak
            timeout=60,
            timeout2=60
        )

        while True:
            # runs poll in a thread catching timeout errors
            r = poll.run()
            if poll.errors:
                save_communicate = False
                break
            if r or isinstance(process.returncode, int):
                break

            # read message in a thread to catch timeout errors
            output = read_message.run()
            if read_message.errors:
                save_communicate = False
                break

            # log message
            if output:
                log.write(output)

        # cmd not frozen and it is save to communicate
        if save_communicate:
            _, err = process.communicate()
        else:  # cmd frozen
            process.terminate()
            raise TimeoutError(
                "Process timed out. Process shut down. Last messages from the process: %s"
                % log.getvalue()
            )

        # cmd failed
        if process.returncode:
            raise RuntimeError(
                "Return code: %(ret_code)s Error message: %(err_msg)s"
                % {"ret_code": process.returncode, "err_msg": err}
            )

        # cmd passed but with errors
        if err:
            module_logger().warning(
                "Process terminated but reported the following error or warning: \n\t %s" % err)

            exit_status = process.returncode

    return exit_status


def check_output(command):
    operation_system = sys.platform

    shell = False
    if operation_system == 'win32' or operation_system == 'cygwin':
        shell = True

    return subprocess.check_output(command, shell=shell).decode("utf-8")

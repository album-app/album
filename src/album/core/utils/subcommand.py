import io
import signal
import subprocess
import sys
import threading

import pexpect

from album.runner import album_logging
from album.runner.album_logging import LogfileBuffer

module_logger = album_logging.get_active_logger


class SaveThreadWithReturn:
    """Class running an action in a python thread. If action runs in timeout, action2 is executed. After timeout 2, the
    action is terminated.

    Attributes:
        name:
            the name of the action
        action:
            the action to call
        action2:
            action2 to call when action runs in first timeout
        timeout:
            time, after which action2 is executed.
        timeout2:
            time, after which action is terminated with error
        parent_thread_name:
            name of thread from which this thread is started

    """

    def __init__(self, name, action, action2=None, timeout=1, timeout2=5, parent_thread_name=None):
        if not callable(action):
            raise ValueError("Action needs to be callable!")

        if action2:
            if not callable(action2):
                raise ValueError("Action2 needs to be callable if set!")
        else:
            action2 = self.stop

        self.name = name
        self.action = action
        self.action2 = action2
        self.timeout = timeout
        self.timeout2 = timeout2
        self.errors = False
        self.thread = None
        self.thread_id = -1
        self.parent_thread_name = parent_thread_name
        self.return_value = None

    def run(self):
        """run the thread. Starting the action"""

        self.thread = threading.Thread(target=self.run_action)
        self.thread.daemon = True  # important for the main python to be able to finish
        self.thread.start()
        self.thread.join(self.timeout)

        if self.thread.is_alive():
            self.action2()
            self.thread.join(self.timeout2)
            if self.thread.is_alive():
                self._stop_routine()

        return self.return_value

    def run_action(self):
        album_logging.configure_logging(self.name, parent_name=self.parent_thread_name)
        self.return_value = self.action()
        album_logging.pop_active_logger()

    def _stop_routine(self):
        self.thread_id = self.thread.ident
        self.errors = True
        self.stop()
        return None

    def stop(self):
        """Stops the thread."""
        if sys.platform == 'win32' or sys.platform == 'cygwin':
            # there is no easy way to send a signal from one thread to another...
            pass
        else:
            signal.pthread_kill(self.thread_id, signal.SIGKILL)


def run(command, log_output=True, message_formatter=None, timeout1=60, timeout2=120, pipe_output=True):
    """Runs a command in a subprocess thereby logging its output.

    Args:
        log_output:
            Indicates whether to log the output of the subprocess or not.
        message_formatter:
            Possibility to parse a lambda to format the message in a certain way.
        command:
            The command to run.
        timeout1:
            The timeout in seconds after which a rescue operation (enter) is send to the process.
            Timeout resets when subprocess gives feedback to the main process.
            WindowsOS option only. Default: 60s
        timeout2:
            The timeout in seconds after timeout 1 has unsuccessfully passed, after which the process is declared dead.
            Timeout resets when subprocess gives feedback to the main process.
            WindowsOS option only. Default: 120s
        pipe_output:
            Indicates whether to pipe the output of the subprocess or just return it as is.

    Returns:
        Exit status of the subprocess.

    Raises:
        RuntimeError:
            When exit-status of subprocess is not 0.

    """

    module_logger().debug('Running command: %s...' % " ".join(command))
    exit_status = 1

    logger = album_logging.configure_logging("subcommand")
    log = LogfileBuffer(message_formatter)
    log.module_logger = lambda: logger
    if not log_output:
        log = io.StringIO()

    operation_system = sys.platform
    if operation_system == 'linux' or operation_system == 'darwin':
        exit_status = _run_process_linux_macos(command, exit_status, log, pipe_output)
    else:
        exit_status = _run_process_windows(command, exit_status, log, timeout1, timeout2, pipe_output)

    album_logging.pop_active_logger()
    return exit_status


def _run_process_linux_macos(command, exit_status, log, pipe_output):
    if pipe_output:
        (command_output, exit_status) = pexpect.run(
            " ".join(command), logfile=log, withexitstatus=1, timeout=None, encoding=sys.getfilesystemencoding()
        )
        if exit_status != 0:
            module_logger().error(command_output)
            album_logging.pop_active_logger()
            raise RuntimeError("Command " + " ".join(command) + " failed: " + command_output)
        return exit_status
    else:
        return subprocess.run(command)


def _run_process_windows(command, exit_status, log, timeout1, timeout2, pipe_output):
    if pipe_output:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1,  # line buffered
            shell=True
        )
        save_communicate = True
        current_logger_name = album_logging.get_active_logger().name
        poll = SaveThreadWithReturn("poll", process.poll, parent_thread_name=current_logger_name)
        read_message = SaveThreadWithReturn(
            "reader",
            process.stdout.readline,
            lambda: process.stdin.write("\r\n"),  # after 60 seconds of no feedback try to send a linebreak
            timeout=timeout1,
            timeout2=timeout2,
            parent_thread_name=current_logger_name
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
            album_logging.pop_active_logger()
            raise TimeoutError(
                "Process timed out. Process shut down. Last messages from the process: %s"
                % log.getvalue()
            )
        # cmd failed
        if process.returncode:
            err_msg = err if err else log.getvalue()
            album_logging.pop_active_logger()
            raise RuntimeError(
                "{\"ret_code\": %(ret_code)s, \"err_msg\": %(err_msg)s}"
                % {"ret_code": process.returncode, "err_msg": err_msg}
            )
        # cmd passed but with errors
        if err:
            module_logger().warning(
                "Process terminated but reported the following error or warning: \n\t %s" % err)

            exit_status = process.returncode
        return exit_status
    else:
        process = subprocess.run(
            command,
            universal_newlines=True,
            bufsize=1,  # line buffered
            shell=True
        )


def check_output(command):
    """Runs a command thereby checking its output."""
    operation_system = sys.platform

    shell = False
    if operation_system == 'win32' or operation_system == 'cygwin':
        shell = True

    return subprocess.check_output(command, shell=shell).decode("utf-8")

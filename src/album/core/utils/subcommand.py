import io
import re
import signal
import subprocess
import sys
import threading
from typing import Optional

import pexpect
from album.runner.album_logging import get_active_logger, LogEntry, LogLevel

from album.runner import album_logging

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


class LogfileBuffer(io.StringIO):
    """Class for logging in a subprocess. Logs to the current active logger."""

    def __init__(self, message_formatter=None):
        super().__init__()
        self.message_formatter = message_formatter
        self.leftover_message = None
        self.last_level = None

    def write(self, input_string: str) -> int:
        messages = self.split_messages(input_string)

        for m in messages:
            s = self.tabulate_multi_lines(m)

            log_entry = self.parse_log(s)

            if log_entry:

                if self.message_formatter and callable(self.message_formatter):
                    message = self.message_formatter(log_entry.message)
                else:
                    message = log_entry.message

                old_name = get_active_logger().name
                if not log_entry.name:
                    log_entry.name = old_name
                else:
                    get_active_logger().name = log_entry.name

                self._log(log_entry.level, message)

                self.last_level = log_entry.level
                get_active_logger().name = old_name

            else:  # unknown message not using print or logging.
                if self.last_level:
                    self._log(self.last_level, s)
                else:
                    self._log('INFO', s)

        return 1

    def _log(self, current_level, message):
        if LogLevel.INFO.name == current_level:
            get_active_logger().info(message)
        elif LogLevel.DEBUG.name == current_level:
            get_active_logger().debug(message)
        elif LogLevel.WARNING.name == current_level:
            get_active_logger().warning(message)
        else:
            get_active_logger().error(message)

    def split_messages(self, s: str):
        # init empty return val
        messages = []

        if self.leftover_message:
            s = self.leftover_message + s
            self.leftover_message = None

        # split
        split_s = s.split("\n")

        # strip - all message that are not interrupted
        split_i = [l.strip() for l in split_s[:-1]]

        # last message might be interrupted through buffer-size
        if not split_s[-1].endswith("\n"):
            self.leftover_message = split_s[-1]
        else:
            split_i.append(split_s[-1].strip())

        for l in split_i:
            log_entry = self.parse_log(l)

            if log_entry:  # pattern found
                messages.append(l)
            else:  # pattern not found
                if len(messages) > 0:  # message part of previous message
                    messages[-1] += "\n" + l
                else:  # message standalone
                    messages.append(l)

        return messages

    @staticmethod
    def tabulate_multi_lines(s: str, indent=2):
        split_s = s.strip().split("\n")
        r = split_s[0].strip()
        if len(split_s) > 1:
            r = r + "\n"
            for l in split_s[1:]:
                r = r + "".join(["\t"] * indent) + l.strip() + "\n"
        return r.strip()

    @staticmethod
    def parse_log(text) -> Optional[LogEntry]:
        # regex for log level
        regex_log_level = "|".join([l.name for l in LogLevel])
        # regex for log message.
        regex_text = '([^ - ]+) - (%s) -([\s\S]+)?' % regex_log_level
        # search
        r = re.search(regex_text, text)

        if not r:
            regex_text = '([\s\S]+) (%s) ([\s\S]+)?' % regex_log_level
            r = re.search(regex_text, text)
            if not r:
                regex_text = '(%s):([\s\S]+)?' % regex_log_level
                r = re.search(regex_text, text)
            if not r:
                regex_text = '\[(%s)\] ([\s\S]+)?' % regex_log_level
                r = re.search(regex_text, text)
        if r:
            if len(r.groups()) == 3:
                name = r.group(1)
                level = r.group(2)
                message = r.group(3)
            else:
                name = None
                level = r.group(1)
                message = r.group(2)
            if message:
                message = message.strip(" ")
            else:
                message = ""
            return LogEntry(name, level, message)
        return None


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

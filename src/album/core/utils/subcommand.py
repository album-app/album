import io
import os
import re
import subprocess
import threading
from typing import Optional

from album.runner import album_logging
from album.runner.album_logging import LogEntry, LogLevel
from album.runner.core.api.model.solution_script import ISolutionScript

module_logger = album_logging.get_active_logger


class LogfileBuffer(io.StringIO):
    """Class for logging in a subprocess. Logs to the current active logger."""

    def __init__(self, module_logger, message_formatter='%(message)s', error_logger = False):
        super().__init__()
        self.message_formatter = message_formatter
        self.leftover_message = None
        self.last_log = None
        self.is_error_logger = error_logger
        self.logger = module_logger

    def write(self, input) -> int:
        if not isinstance(input, str):
            input = str(input, "utf-8")
        m = input.rstrip()

        log_entry = self.parse_log(m)
        old_name = self.logger.name

        if log_entry:

            if log_entry.name:
                if log_entry.name == 'root':
                    log_entry.name = self.logger.name
                else:
                    if log_entry.name.startswith('root.'):
                        log_entry.name = log_entry.name.replace('root.', '')
                    log_entry.name = self.logger.name + "." + log_entry.name

            if self.message_formatter and callable(self.message_formatter):
                message = self.message_formatter(log_entry.message)
            else:
                message = log_entry.message

            if log_entry.name:
                self.logger.name = log_entry.name

            self._log(log_entry.level, message)
        else:  # unknown message not using or logging.
            self.logger.name = old_name + '.script'
            if self.is_error_logger:
                self._log('ERROR', m)
            else:
                self._log('INFO', m)
        self.logger.name = old_name
        #
        return 1

    def _log(self, current_level, message):
        if LogLevel.INFO.name == current_level:
            self.logger.info(message)
        elif LogLevel.DEBUG.name == current_level:
            self.logger.debug(message)
        elif LogLevel.WARNING.name == current_level:
            self.logger.warning(message)
        elif LogLevel.ERROR.name == current_level:
            self.logger.error(message)
        else:
            self.logger.info(message)

    @staticmethod
    def parse_log(text) -> Optional[LogEntry]:
        # regex for log level
        regex_log_level = "DEBUG|INFO|WARNING|ERROR"
        # regex for log message.
        # search
        r = re.search(ISolutionScript.get_script_logging_formatter_regex(), text)
        message = None
        name = None
        level = None
        if r:
            name = r.group(3)
            level = r.group(2)
            message = r.group(4)
        else:
            regex_text = '(%s): ([\s\S]+)?' % regex_log_level
            r = re.search(regex_text, text)
            if r:
                name = None
                level = r.group(1)
                message = r.group(2)
            else:
                regex_text = '\[(%s)\] ([\s\S]+)?' % regex_log_level
                r = re.search(regex_text, text)
                if r:
                    name = None
                    level = r.group(1)
                    message = r.group(2)
                else:
                    regex_text = '(%s)\s+([\s\S]+) - ([\s\S]+)?' % regex_log_level
                    r = re.search(regex_text, text)
                    if r:
                        name = r.group(2)
                        level = r.group(1)
                        message = r.group(3)
        if message:
            message = message.rstrip(" ")
            return LogEntry(name, level, message)
        else:
            return None


class LogProcessing:
    def __init__(self, logger, log_output, message_formatter):
        if log_output:
            self.info_logger = LogfileBuffer(logger, message_formatter)
            self.error_logger = LogfileBuffer(logger, message_formatter, error_logger=True)
        else:
            self.info_logger = io.StringIO()
            self.error_logger = io.StringIO()

    def log_info(self, s):
        self.info_logger.write(s)

    def log_error(self, s):
        self.error_logger.write(s)

    def close(self):
        self.info_logger.close()
        self.error_logger.close()


def run(command, log_output=True, message_formatter=None, pipe_output=True):
    """Runs a command in a subprocess thereby logging its output.

    Args:
        log_output:
            Indicates whether to log the output of the subprocess or not.
        message_formatter:
            Possibility to parse a lambda to format the message in a certain way.
        command:
            The command to run.
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

    logger = album_logging.get_active_logger()
    log_processing = LogProcessing(logger, log_output, message_formatter)

    exit_status = _run_process(command, exit_status, log_processing, pipe_output)

    return exit_status


class SubProcessError(RuntimeError):

    def __init__(self, exit_status, message) -> None:
        self.exit_status = exit_status
        super().__init__(message)


class LogPipe(threading.Thread):
    """derived from https://gist.github.com/alfredodeza/dcea71d5c0234c54d9b1"""

    def __init__(self, logger):
        """Setup the object with a logger and a loglevel
        and start the thread
        """
        threading.Thread.__init__(self)
        self.daemon = False
        self.logger = logger
        self.fdRead, self.fdWrite = os.pipe()
        self.pipeReader = os.fdopen(self.fdRead)
        self.process = None
        self.start()

    def fileno(self):
        """Return the write file descriptor of the pipe
        """
        return self.fdWrite

    def run(self):
        """Run the thread, logging everything.
        """
        for line in iter(self.pipeReader.readline, ''):
            self.logger.write(line.strip('\n'))

        self.pipeReader.close()

    def close(self):
        """Close the write end of the pipe.
        """
        os.close(self.fdWrite)


def _run_process(command, exit_status, log: LogProcessing, pipe_output):
    if pipe_output:
        stdout = log.info_logger
        stderr = log.error_logger
        info_pipe = LogPipe(stdout)
        error_pipe = LogPipe(stderr)
        p = subprocess.Popen(
            command,
            stdout=info_pipe,
            stderr=error_pipe,
            bufsize=1,
            universal_newlines=True
        )
        p.wait()
        info_pipe.close()
        error_pipe.close()
        log.close()
        if p.returncode != 0:
            raise SubProcessError(exit_status, p.returncode)
        return exit_status
    else:
        return subprocess.run(command)


def check_output(command):
    """Runs a command thereby checking its output."""
    return subprocess.check_output(command).decode("utf-8")

import io
import re
import subprocess
import sys
from typing import Optional

from album.runner import album_logging
from album.runner.album_logging import LogEntry, LogLevel

module_logger = album_logging.get_active_logger


class LogfileBuffer(io.StringIO):
    """Class for logging in a subprocess. Logs to the current active logger."""

    def __init__(
        self, module_logger, message_formatter="%(message)s", error_logger=False
    ):
        super().__init__()
        self.message_formatter = message_formatter
        self.leftover_message = None
        self.last_log = None
        self.is_error_logger = error_logger
        self.logger = module_logger
        self.logger_name = self.logger.name
        self.logger_name_script = self.logger_name + ".script"
        self.logger_name_current = self.logger_name_script
        self.logger_name_unnamed = self.logger_name_script + ".log"

    def write(self, input) -> int:
        if not isinstance(input, str):
            input = str(input, "utf-8")
        m = input.rstrip()

        log_entry = self.parse_log(m)

        if log_entry:

            if log_entry.name:
                log_entry.name = log_entry.name.strip()
                if log_entry.name.startswith("root.script"):
                    log_entry.name = log_entry.name.lstrip("root.script")
                    log_entry.name = log_entry.name.lstrip(".")
                if len(log_entry.name) > 0:
                    log_entry.name = self.logger_name_script + "." + log_entry.name
                else:
                    log_entry.name = self.logger_name_script
            else:
                log_entry.name = self.logger_name_unnamed

            if self.message_formatter and callable(self.message_formatter):
                message = self.message_formatter(log_entry.message)
            else:
                message = log_entry.message
            self.logger_name_current = log_entry.name
            self.logger.name = log_entry.name
            self._log(log_entry.level, message)
        else:  # unknown message not using or logging.
            self.logger.name = self.logger_name_current
            if self.is_error_logger:
                self._log("ERROR", m)
            else:
                self._log("INFO", m)
        self.logger.name = self.logger_name
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
        res = LogfileBuffer._parse_album_runner_log(text)
        if not res:
            res = LogfileBuffer._parse_album_log(text)
            if not res:
                res = LogfileBuffer._parse_level_colon_log(text)
                if not res:
                    res = LogfileBuffer._parse_level_brackets_log(text)
        if res:
            if res.message:
                res.message = res.message.rstrip(" ")
            return res
        else:
            return None

    @staticmethod
    def get_script_logging_formatter_regex():
        regex_log_level = "DEBUG|INFO|WARNING|ERROR"
        return r"(%s)\s+([\s\S]+) - ([\s\S]+)?" % regex_log_level

    @staticmethod
    def _parse_album_runner_log(text):
        r = re.search(LogfileBuffer.get_script_logging_formatter_regex(), text)
        if r:
            return LogEntry(name=r.group(2), level=r.group(1), message=r.group(3))
        return None

    @staticmethod
    def _parse_album_log(text):
        r = re.search(
            r"\d\d:\d\d:\d\d (%s)(?:[\s]+(~*))? ([\s\S]+)?"
            % LogfileBuffer._regex_log_level(),
            text,
        )
        if r:
            if len(r.groups()) == 3:
                name = r.group(2)
                if name != None and len(name) == 0:
                    name = None
                return LogEntry(name=name, level=r.group(1), message=r.group(3))
            else:
                return LogEntry(name=None, level=r.group(1), message=r.group(2))
        return None

    @staticmethod
    def _parse_level_colon_log(text):
        r = re.search(r"(%s): ([\s\S]+)?" % LogfileBuffer._regex_log_level(), text)
        if r:
            return LogEntry(name=None, level=r.group(1), message=r.group(2))
        return None

    @staticmethod
    def _parse_level_brackets_log(text):
        r = re.search(r"\[(%s)\] ([\s\S]+)?" % LogfileBuffer._regex_log_level(), text)
        if r:
            return LogEntry(name=None, level=r.group(1), message=r.group(2))
        return None

    @staticmethod
    def _regex_log_level():
        return "DEBUG|INFO|WARNING|ERROR"


class LogProcessing:
    def __init__(self, logger, log_output, message_formatter):
        if log_output:
            self.info_logger = LogfileBuffer(logger, message_formatter)
            self.error_logger = LogfileBuffer(
                logger, message_formatter, error_logger=True
            )
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
    module_logger().debug("Running command: %s..." % " ".join(command))

    logger = album_logging.get_active_logger()
    log_processing = LogProcessing(logger, log_output, message_formatter)

    exit_status = _run_process(command, log_processing, pipe_output)

    return exit_status


class SubProcessError(RuntimeError):
    def __init__(self, exit_status, message) -> None:
        self.exit_status = exit_status
        super().__init__(message)


def _run_process(command, log: LogProcessing, pipe_output):
    if pipe_output:
        process = subprocess.Popen(
            command,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        while True:
            output = process.stdout.readline()
            if process.poll() is not None:
                break
            if output:
                log.log_info(output.rstrip())
        sys.stdout.flush()
        rc = process.poll()
        if rc != 0:
            raise SubProcessError(rc, "ERROR while running %s" % " ".join(command))
        return rc
    else:
        return subprocess.run(command)


def check_output(command):
    """Runs a command thereby checking its output."""
    return subprocess.check_output(command).decode("utf-8")

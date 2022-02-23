import io
import logging
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from io import StringIO
from logging import StreamHandler
from unittest.mock import MagicMock

from album.core.utils import subcommand
from album.core.utils.subcommand import LogfileBuffer, SubProcessError, LogPipe
from album.runner import album_logging
from album.runner.album_logging import pop_active_logger, get_active_logger, get_active_logger_in_thread, \
    push_active_logger
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestSubcommand(TestUnitCoreCommon):
    def setUp(self):
        super().setUp()

    def test_run(self):
        handler = StreamHandler()
        self.logger.addHandler(handler)
        self.logger.setLevel("DEBUG")
        info = MagicMock(return_value=None)
        handler.handle = info
        subcommand.run(["echo", "test"])
        self.assertTrue(info.call_count > 1)
        name1, args1, kwargs1 = info.mock_calls[0]
        name2, args2, kwargs2 = info.mock_calls[1]
        self.assertTrue("Running command: echo test...", args1[0].msg)
        self.assertEqual("test", args2[0].msg)

    def test_run_python(self):
        handler = StreamHandler()
        self.logger.addHandler(handler)
        self.logger.setLevel("DEBUG")
        info = MagicMock(return_value=None)
        handler.handle = info

        fd, path = tempfile.mkstemp()
        try:
            with os.fdopen(fd, 'w') as tmp:
                tmp.write('print(\'nothing happening\')\n')
            subcommand.run(["python", path])
        finally:
            os.remove(path)

        self.assertTrue(info.call_count == 2)
        name1, args1, kwargs1 = info.mock_calls[0]
        name2, args2, kwargs2 = info.mock_calls[1]
        self.assertTrue("Running command: python %s..." % path, args1[0].msg)
        self.assertEqual("nothing happening", args2[0].msg)

    def test_run_throw_error(self):
        handler = StreamHandler()
        self.logger.addHandler(handler)
        self.logger.setLevel("DEBUG")
        info = MagicMock(return_value=None)
        handler.handle = info

        fd, path = tempfile.mkstemp()
        try:
            with os.fdopen(fd, 'w') as tmp:
                tmp.write('raise RuntimeError(\'this should not happen\')\n')
            with self.assertRaises(SubProcessError):
                subcommand.run(["python", path])
        finally:
            os.remove(path)

        self.assertTrue(info.call_count == 5)
        name1, args1, kwargs1 = info.mock_calls[0]
        name2, args2, kwargs2 = info.mock_calls[1]
        name6, args6, kwargs6 = info.mock_calls[4]
        self.assertTrue("Running command: python %s..." % path, args1[0].msg)
        self.assertIn("Traceback", args2[0].msg)
        self.assertIn("RuntimeError: this should not happen", args6[0].msg)

    def test_run_print_to_stderr(self):
        handler = StreamHandler()
        self.logger.addHandler(handler)
        self.logger.setLevel("DEBUG")
        info = MagicMock(return_value=None)
        handler.handle = info

        fd, path = tempfile.mkstemp()
        try:
            with os.fdopen(fd, 'w') as tmp:
                tmp.write('import sys\nprint(\'this should not happen\', file = sys.stderr)\n')
            subcommand.run(["python", path])
        finally:
            os.remove(path)

        self.assertTrue(info.call_count == 2)
        name1, args1, kwargs1 = info.mock_calls[0]
        name2, args2, kwargs2 = info.mock_calls[1]
        self.assertTrue("Running command: python %s..." % path, args1[0].msg)
        self.assertIn("this should not happen", args2[0].msg)

    def test_run_iteratively_throw_error(self):
        handler = StreamHandler()
        self.logger.addHandler(handler)
        self.logger.setLevel("DEBUG")
        info = MagicMock(return_value=None)
        handler.handle = info
        subcommand.run(["echo", "test"])
        self.assertTrue(info.call_count > 1)
        name1, args1, kwargs1 = info.mock_calls[0]
        name2, args2, kwargs2 = info.mock_calls[1]
        self.assertTrue("Running command: echo test...", args1[0].msg)
        self.assertEqual("test", args2[0].msg)

    def test_run_logging_from_thread(self):
        self.logger.setLevel("DEBUG")
        thread = threading.Thread(target=self._run_in_thread, args=(threading.current_thread().ident,))
        thread.start()
        thread.join()

    def _run_in_thread(self, parent_thread_id):
        album_logging.configure_logging("thread", parent_thread_id=parent_thread_id)
        self.test_run()


class TestLogPipe(TestUnitCoreCommon):

    def test_multiple_subprocess_pipe_calls(self):
        # calling this repeatedly is catching potential bad file descriptor errors
        self.log_subprocess()
        self.log_subprocess()

    def log_subprocess(self):
        logpipe = LogPipe(io.StringIO())
        logpipe2 = LogPipe(io.StringIO())
        p = subprocess.Popen(
            ['echo', 'bla'],
            stdout=logpipe,
            stderr=logpipe2
        )
        p.wait()
        logpipe.close()
        logpipe2.close()


class TestLogfileBuffer(TestUnitCoreCommon):

    def tearDown(self) -> None:
        pop_active_logger()
        super().tearDown()

    def test_write(self):
        self.assertIsNotNone(get_active_logger())

        log_buffer = LogfileBuffer(get_active_logger())
        log_buffer.write("app1 - WARNING - message\n over \n several \n lines\n")
        log_buffer.write("DEBUG: - d\nasfasdfsadfasdfasdfsadfasdfasdfasdfasdfw\n")
        log_buffer.write("16:07:16 DEBUG  name: - d\nfghfgh\n")
        log_buffer.write("asfasdfsadfa\ng\napp1 - INFO - i\no\ns\nl\n")

        logs = self.get_logs()
        self.assertIn("app1 - WARNING - message", logs[0])
        self.assertEqual(" over ", logs[1])
        self.assertEqual(" several ", logs[2])
        self.assertIn(" lines", logs[3])
        self.assertIn("asfasdfsadfa", logs[4])
        self.assertEqual("g", logs[5])
        self.assertIn("app1 - INFO - i", logs[6])
        self.assertEqual("o", logs[7])
        self.assertEqual("s", logs[8])
        self.assertIn("l", logs[9])

    @unittest.skipIf(sys.platform == 'darwin', "Multiprocessing broken for MACOS!")
    def test_multiprocessing(self):
        capture_output1 = StringIO()
        capture_output2 = StringIO()
        thread1 = threading.Thread(target=self.log_in_thread, args=("thread1", capture_output1))
        thread2 = threading.Thread(target=self.log_in_thread, args=("thread2", capture_output2))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        self.assertFalse(thread1.is_alive())
        self.assertFalse(thread2.is_alive())

        logger1 = get_active_logger_in_thread(thread1.ident)
        logger2 = get_active_logger_in_thread(thread2.ident)

        self.assertIsNotNone(logger1)
        self.assertIsNotNone(logger2)
        self.assertNotEqual(logger1, get_active_logger())
        self.assertNotEqual(logger2, get_active_logger())
        self.assertNotEqual(logger1, logger2)

        logs1 = self.as_list(capture_output1.getvalue())
        logs2 = self.as_list(capture_output2.getvalue())

        self.assertEqual(100, len(logs1))
        self.assertEqual(100, len(logs2))
        all(self.assertTrue(elem.startswith("thread1")) for elem in logs1)
        all(self.assertTrue(elem.startswith("thread2")) for elem in logs2)

    def test_parse_log(self):
        log_buffer = LogfileBuffer(get_active_logger())

        res = log_buffer.parse_log("14:15:12 WARNING name - message")
        self.assertEqual("name", res.name)
        self.assertEqual("WARNING", res.level)
        self.assertEqual("message", res.message)

        res = log_buffer.parse_log("14:15:12 WARNING   message")
        self.assertEqual(None, res.name)
        self.assertEqual("WARNING", res.level)
        self.assertEqual("message", res.message)

        res = log_buffer.parse_log("14:15:12 WARNING message")
        self.assertEqual(None, res.name)
        self.assertEqual("WARNING", res.level)
        self.assertEqual("message", res.message)

        res = log_buffer.parse_log("14:15:12 WARNING  ~ message")
        self.assertEqual("~", res.name)
        self.assertEqual("WARNING", res.level)
        self.assertEqual("message", res.message)

        res = log_buffer.parse_log("14:15:12 WARNING  ~~ message")
        self.assertEqual("~~", res.name)
        self.assertEqual("WARNING", res.level)
        self.assertEqual("message", res.message)

        res = log_buffer.parse_log("WARNING name - message")
        self.assertEqual("name", res.name)
        self.assertEqual("WARNING", res.level)
        self.assertEqual("message", res.message)

        res = log_buffer.parse_log("INFO    root.script - message")
        self.assertEqual("root.script", res.name)
        self.assertEqual("INFO", res.level)
        self.assertEqual("message", res.message)

        res = log_buffer.parse_log("15:22:24.487 [SciJava-7e75bf2d-Thread-0] DEBUG message")
        self.assertIsNone(res)

        res = log_buffer.parse_log("[WARNING] message")
        self.assertEqual(None, res.name)
        self.assertEqual("WARNING", res.level)
        self.assertEqual("message", res.message)

        res = log_buffer.parse_log("WARNING: message")
        self.assertEqual(None, res.name)
        self.assertEqual("WARNING", res.level)
        self.assertEqual("message", res.message)

    @staticmethod
    def log_in_thread(name, stream_handler):
        logger = logging.getLogger(name)
        logger.setLevel('INFO')
        ch = logging.StreamHandler(stream_handler)
        ch.setLevel('INFO')
        ch.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(ch)
        push_active_logger(logger)
        log_buffer = LogfileBuffer(get_active_logger())
        for i in range(0, 100):
            log_buffer.write(name + "_" + str(i) + "\n")  # print, logger.info() should all end with a newline

    def get_logs(self):
        return self.as_list(self.captured_output.getvalue())

    @staticmethod
    def as_list(logs):
        logs = logs.strip()
        return logs.split("\n")

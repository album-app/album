import threading
from logging import StreamHandler
from unittest.mock import MagicMock

from album.core.utils import subcommand
from album.runner import logging
from test.unit.test_unit_common import TestUnitCommon


class TestSubcommand(TestUnitCommon):

    def test_run(self):

        handler = StreamHandler()
        self.logger.addHandler(handler)

        info = MagicMock(return_value=None)
        handler.handle = info

        subcommand.run(["echo", "test"])

        self.assertTrue(info.call_count > 1)
        name1, args1, kwargs1 = info.mock_calls[0]
        name2, args2, kwargs2 = info.mock_calls[1]
        self.assertTrue("Running command: echo test...", args1[0].msg)
        self.assertEqual("test", args2[0].msg)

    def test_run_logging_from_thread(self):
        thread = threading.Thread(target=self._run_in_thread, args=(threading.current_thread().ident, ))
        thread.start()
        thread.join()

    def _run_in_thread(self, parent_thread_id):
        logging.configure_logging("thread", parent_thread_id=parent_thread_id)
        self.test_run()

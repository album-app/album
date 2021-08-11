import unittest.mock
from logging import getLogger

from album.core.model.log_handler import LogHandler
from album_runner import logging
from album_runner.logging import LogLevel
from test.unit.test_unit_common import TestUnitCommon


class TestLogHandler(TestUnitCommon):

    def test_handler(self):
        self.logger.setLevel(20)
        handler1 = LogHandler()
        self.logger.addHandler(handler1)
        self.logger.info("test_handler_test1")
        self.logger.error("test_handler_test2")
        self.logger.removeHandler(handler1)
        handler2 = LogHandler()
        self.assertEqual(2, len(handler1.records))
        self.assertEqual(0, len(handler2.records))
        self.assertNotEqual(handler1, handler2)
        self.logger.addHandler(handler2)
        self.logger.info("test_handler_test3")
        self.logger.removeHandler(handler2)
        self.assertEqual(2, len(handler1.records))
        self.assertEqual("test_handler_test1", handler1.records[0].msg)
        self.assertEqual("test_handler_test2", handler1.records[1].msg)
        self.assertEqual(1, len(handler2.records))
        self.assertEqual("test_handler_test3", handler2.records[0].msg)

    def test_logging_hierarchy(self):
        handler = LogHandler()
        self.assertEqual(0, len(handler.records))
        self.logger.addHandler(handler)
        self.assertEqual(0, len(handler.records))
        child_logger = logging.configure_logging("test", loglevel=LogLevel.INFO)
        child_logger.info("test_logging_hierarchy_test1")
        child_logger.error("test_logging_hierarchy_test2")
        logging.pop_active_logger()
        self.logger.removeHandler(handler)
        self.logger.info("test_logging_hierarchy_test3")
        self.assertEqual(2, len(handler.records))
        self.assertEqual("test_logging_hierarchy_test1", handler.records[0].msg)
        self.assertEqual("test_logging_hierarchy_test2", handler.records[1].msg)

    def test_logging_hierarchy_default_loggers(self):
        handler = LogHandler()
        self.logger.setLevel(20)
        self.logger.addHandler(handler)
        child_logger = getLogger(self.logger.name + ".child")
        child_logger.setLevel(20)
        child_logger.error("test1")
        child_logger.error("test2")
        self.logger.removeHandler(handler)
        self.logger.info("test3")
        self.assertEqual(2, len(handler.records))
        self.assertEqual("test1", handler.records[0].msg)
        self.assertEqual("test2", handler.records[1].msg)


if __name__ == '__main__':
    unittest.main()

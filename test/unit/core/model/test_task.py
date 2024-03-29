import unittest.mock
from logging import getLogger

from album.core.model.task import LogHandler
from album.runner import album_logging
from album.runner.album_logging import LogLevel
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestLogHandler(TestUnitCoreCommon):
    def setUp(self):
        super().setUp()

    def test_handler(self):
        self.logger.setLevel(20)
        handler1 = LogHandler()
        self.logger.addHandler(handler1)
        self.logger.info("test_handler_test1")
        self.logger.error("test_handler_test2")
        self.logger.removeHandler(handler1)
        handler2 = LogHandler()
        self.assertEqual(2, len(handler1._records))
        self.assertEqual(0, len(handler2._records))
        self.assertNotEqual(handler1, handler2)
        self.logger.addHandler(handler2)
        self.logger.info("test_handler_test3")
        self.logger.removeHandler(handler2)
        self.assertEqual(2, len(handler1._records))
        self.assertEqual("test_handler_test1", handler1._records[0].msg)
        self.assertEqual("test_handler_test2", handler1._records[1].msg)
        self.assertEqual(1, len(handler2._records))
        self.assertEqual("test_handler_test3", handler2._records[0].msg)

    def test_logging_hierarchy(self):
        handler = LogHandler()
        self.assertEqual(0, len(handler._records))
        self.logger.addHandler(handler)
        self.assertEqual(0, len(handler._records))
        child_logger = album_logging.configure_logging("test", loglevel=LogLevel.INFO)
        child_logger.info("test_logging_hierarchy_test1")
        child_logger.error("test_logging_hierarchy_test2")
        album_logging.pop_active_logger()
        self.logger.removeHandler(handler)
        self.logger.info("test_logging_hierarchy_test3")
        self.assertEqual(2, len(handler._records))
        self.assertEqual("test_logging_hierarchy_test1", handler._records[0].msg)
        self.assertEqual("test_logging_hierarchy_test2", handler._records[1].msg)

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
        self.assertEqual(2, len(handler._records))
        self.assertEqual("test1", handler._records[0].msg)
        self.assertEqual("test2", handler._records[1].msg)


class TestTask(TestUnitCoreCommon):
    def setUp(self):
        pass

    def tearDown(self) -> None:
        pass

    # todo: implement


if __name__ == "__main__":
    unittest.main()

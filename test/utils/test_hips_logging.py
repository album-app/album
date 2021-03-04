
import unittest

from utils.hips_logging import *


def helper_test_configure_logging(logger):
    handler_levels = []
    for handler in logger.handlers:
        handler_levels.append(logging.getLevelName(handler.level))

    return handler_levels


class TestHipsLogging(unittest.TestCase):

    def setUp(self):
        # all hips logging levels
        self.loglevels = [LogLevel(0), LogLevel(1)]

    def test_to_loglevel(self):

        for level in self.loglevels:
            self.assertEqual(to_loglevel(level.name, None), level)

        with self.assertRaises(KeyError):
            to_loglevel("NotAvailableLogLevel", None)

    def test_configure_logging(self):

        for idx, level in enumerate(self.loglevels):
            # set correct logging level for logger and all logger.handler for all hips logging level
            logger = configure_logging(level, "test_%s" % idx)

            self.assertTrue(logging.getLevelName(logger.level) == level.name)

            handler_levels = helper_test_configure_logging(logger)
            self.assertEqual(handler_levels, [level.name] * len(handler_levels))

    def test_set_loglevel(self):
        init_level = LogLevel(0)
        to_level = LogLevel(1)

        # init logger and check if logging level OK
        logger = configure_logging(init_level, "test")
        self.assertTrue(logging.getLevelName(logger.level) == init_level.name)

        handler_levels = helper_test_configure_logging(logger)
        self.assertEqual(handler_levels, [init_level.name] * len(handler_levels))

        # switch level and check if OK for logger and all logger.handler
        set_loglevel(to_level, "test")

        self.assertTrue(logging.getLevelName(logger.level) == to_level.name)

        handler_levels = helper_test_configure_logging(logger)
        self.assertEqual(handler_levels, [to_level.name] * len(handler_levels))


def test_hips_logging_run():
    run_suite = unittest.TestSuite()
    run_suite.addTests([
        TestHipsLogging('test_to_loglevel'),
        TestHipsLogging('test_configure_logging'),
        TestHipsLogging('test_set_loglevel'),
    ])
    return run_suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(test_hips_logging_run())
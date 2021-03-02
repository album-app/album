import unittest
from test.hips.test_run import test_run_run
from test.hips.test__init__ import test_init_run
from test.install_helper.test_modules import test_modules_run
from test.utils.test_zenodo_api import test_utils_run
from test.utils.test_hips_logging import test_hips_logging_run


def evaluate_result(result: unittest.TestResult):
    if result.wasSuccessful():
        return 0
    return 1


def main():
    runner = unittest.TextTestRunner()
    r = (
        evaluate_result(runner.run(test_run_run())),
        evaluate_result(runner.run(test_init_run())),
        evaluate_result(runner.run(test_modules_run())),
        evaluate_result(runner.run(test_utils_run())),
        evaluate_result(runner.run(test_hips_logging_run())),
    )
    print("%s test suit(s) failed!" % sum(r))

    exit(0) if sum(r) == 0 else exit(1)


main()

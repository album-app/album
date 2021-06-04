import unittest

from test.integration import test_integration_cmdline


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # ### integration
    suite.addTests(loader.loadTestsFromModule(test_integration_cmdline))

    runner = unittest.TextTestRunner(verbosity=3)
    result = runner.run(suite)
    if result.wasSuccessful():
        exit(0)
    else:
        exit(1)


main()

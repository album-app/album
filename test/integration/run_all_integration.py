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
        print("Success")
        exit(0)
    else:
        print("Failed")
        exit(1)


main()

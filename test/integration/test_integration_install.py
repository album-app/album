import sys
import unittest

from hips.argument_parsing import main
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationInstall(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_install_no_install_routine(self):
        # this solution has the no hips_install() configured
        sys.argv = ["", "install", str(self.get_test_solution_path("solution0_dummy_no_routines.py"))]

        # run
        self.assertIsNone(main())

        # assert
        self.assertIn("WARNING - No \"install\" routine configured for solution", self.captured_output.getvalue())

    def test_install(self):
        self.create_test_config()

        # gather arguments
        sys.argv = ["", "install", str(self.get_test_solution_path())]

        self.assertIsNone(main())

        # assert solution was added to local catalog
        self.assertEqual(len(self.test_catalog_collection.local_catalog), 1)

    @unittest.skip("Needs to be implemented!")
    def test_install_with_dependencies(self):
        # ToDo: implement
        pass

    def test_install_no_solution(self):
        sys.argv = ["", "install"]
        with self.assertRaises(SystemExit) as e:
            main()
        self.assertEqual(SystemExit(2).code, e.exception.code)


if __name__ == '__main__':
    unittest.main()

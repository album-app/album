import unittest.mock

from test.unit.test_common import TestHipsCommon


class TestHipsRun(TestHipsCommon):
    def setUp(self):
        """Setup things necessary for all tests of this class"""
        # self.something_all_tests_use = some_value
        pass

    @unittest.skip("Needs to be implemented!")
    def test_set_environment_path(self, _, __):
        pass
        #self.some_hips = hips.Hips(self.attrs)

        #self.assertTrue("/some/path" == hips.run.get_environment_path(self.some_hips), "get_environment_name returns false value!")

    @unittest.skip("Needs to be implemented!")
    def test_run(self):
        # ToDo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_create_run_script(self):
        # ToDo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_environment_exists(self):
        # ToDo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_create_environment(self):
        # ToDo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_run_nested_hips(self):
        # ToDo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__get_environment_dict(self):
        # ToDo: implement
        pass


if __name__ == '__main__':
    unittest.main()

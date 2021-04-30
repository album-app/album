import logging
import os
import sys
import tempfile
import unittest.mock
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import hips.core as hips
from hips.cmdline import main
from hips.core.model.configuration import HipsCatalogConfiguration
from hips.core.model.logging import push_active_logger


# ToDo: CREATE AN INSTALL INTEGRATIONTEST

class TestHIPSCommandLine(unittest.TestCase):
    test_config = """catalogs:
    - https://gitlab.com/ida-mdc/hips-catalog.git
    """

    def setUp(self):
        # make sure no active hips are somehow configured!
        while hips.get_active_hips() is not None:
            hips.pop_active_hips()

    @patch('hips.core.install.HipsCatalogConfiguration')
    def test_install(self, get_conf_mock):
        test_catalog_dir = tempfile.TemporaryDirectory()

        test_config = tempfile.NamedTemporaryFile(delete=False)
        with open(test_config.name, "w") as f:
            self.test_config += "- " + test_catalog_dir.name
            f.writelines(self.test_config)

        config = HipsCatalogConfiguration(test_config.name)

        get_conf_mock.side_effect = [config, config, config]

        self.assertEqual(len(config.local_catalog), 0)

        sys.argv = ["", "install", str(get_test_solution_path())]
        self.assertIsNone(main())

        self.assertEqual(len(config.local_catalog), 1)

    def test_install_no_solution(self):
        sys.argv = ["", "install"]
        with self.assertRaises(SystemExit) as e:
            main()
        self.assertEqual(SystemExit(2).code, e.exception.code)

    def test_search_no_keyword(self):
        sys.argv = ["", "search"]
        with self.assertRaises(SystemExit) as e:
            main()
        self.assertEqual(SystemExit(2).code, e.exception.code)

    def test_search_emtpy_index(self):
        sys.argv = ["", "search", "keyword"]
        self.assertIsNone(main())

    @patch('hips.core.search.HipsCatalogConfiguration')
    @patch('hips.cmdline.__retrieve_logger')
    def test_search_filled_index(self, logger_mock, get_conf_mock):
        # configure additional log output for checking
        captured_output = StringIO()
        logger_mock.side_effect = [configure_test_logging(captured_output)]

        test_config = tempfile.NamedTemporaryFile(delete=False)
        with open(test_config.name, "w") as f:
            self.test_config += "- " + str(Path(get_test_solution_path("")).joinpath("catalog_local"))
            f.writelines(self.test_config)

        # use config in test resources with relative path to a local catalog
        config = HipsCatalogConfiguration(test_config.name)
        get_conf_mock.side_effect = [config]

        # define and run search
        sys.argv = ["", "search", "keyword1"]
        self.assertIsNone(main())

        # check output to have found the solution behind keyword1
        self.assertIn('catalog_local_ida-mdc_solution0_dummy_0.1.0', captured_output.getvalue())

    @patch('hips.core.run.HipsCatalogConfiguration.resolve_from_str')
    def test_run(self, res_from_str_mock):
        sys.argv = ["", "run", get_test_solution_path()]

        res_from_str_mock.side_effect = [{"path": get_test_solution_path(), "catalog": "aCatalog"}]

        self.assertIsNone(main())
        self.assertIsNone(hips.get_active_hips())

    @patch('hips.core.run.HipsCatalogConfiguration.resolve_from_str')
    @patch('hips.core.run.HipsCatalogConfiguration.resolve_hips_dependency')
    @patch('hips.core.run.set_environment_name')
    def test_run_with_parent(self, environment_name_mock, resolve_mock, res_from_str_mock):
        resolve_mock.side_effect = self.__resolve_hips
        environment_name_mock.side_effect = self.__set_environment_name
        res_from_str_mock.side_effect = [{"path": get_test_solution_path("solution1_app1.py"), "catalog": "aCatalog"}]

        fp = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        sys.argv = ["", "run", get_test_solution_path("solution1_app1.py"), "--file", fp.name, "--file_solution1_app1",
                    fp.name, "--app1_param", "value1"]
        self.assertIsNone(main())
        with open(fp.name, "r") as f:
            log = f.read().strip().split("\n")
            self.assertEqual(5, len(log))
            self.assertEqual("app1_run", log[0])
            self.assertEqual("app1_param=value1", log[1])
            self.assertEqual("solution1_app1_run", log[2])
            self.assertEqual("solution1_app1_close", log[3])
            self.assertEqual("app1_close", log[4])
            self.assertIsNone(hips.get_active_hips())

    @patch('hips.core.run.HipsCatalogConfiguration.resolve_from_str')
    @patch('hips.core.run.HipsCatalogConfiguration.resolve_hips_dependency')
    @patch('hips.core.run.set_environment_name')
    def test_run_with_steps(self, run_environment_mock, run_resolve_mock, res_from_str_mock):
        run_resolve_mock.side_effect = self.__resolve_hips
        run_environment_mock.side_effect = self.__set_environment_name
        res_from_str_mock.side_effect = [{"path": get_test_solution_path("hips_with_steps.py"), "catalog": "aCatalog"}]

        fp = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        sys.argv = ["", "run", get_test_solution_path("hips_with_steps.py"), "--file", fp.name, "--file_solution1_app1",
                    fp.name]
        self.assertIsNone(main())
        with open(fp.name, "r") as f:
            log = f.read().strip().split("\n")
            self.assertEqual(12, len(log))
            self.assertEqual("app1_run", log[0])
            self.assertEqual("app1_param=app1_param_value", log[1])
            self.assertEqual("solution1_app1_run", log[2])
            self.assertEqual("solution1_app1_close", log[3])
            self.assertEqual("app1_close", log[4])
            self.assertEqual("app1_run", log[5])
            self.assertEqual("app1_param=app1_param_other_value", log[6])
            self.assertEqual("solution2_app1_run", log[7])
            self.assertEqual("solution2_app1_close", log[8])
            self.assertEqual("app1_close", log[9])
            self.assertEqual("solution3_noparent_run", log[10])
            self.assertEqual("solution3_noparent_close", log[11])
            self.assertIsNone(hips.get_active_hips())

    @patch('hips.core.run.HipsCatalogConfiguration.resolve_from_str')
    @patch('hips.core.run.HipsCatalogConfiguration.resolve_hips_dependency')
    @patch('hips.core.run.set_environment_name')
    def test_run_with_grouped_steps(self, run_environment_mock, run_resolve_mock, res_from_str_mock):
        run_resolve_mock.side_effect = self.__resolve_hips
        run_environment_mock.side_effect = self.__set_environment_name
        res_from_str_mock.side_effect = [
            {"path": get_test_solution_path("hips_with_steps_grouped.py"), "catalog": "aCatalog"}
        ]

        fp = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        sys.argv = ["", "run", get_test_solution_path("hips_with_steps_grouped.py"), "--file", fp.name,
                    "--file_solution1_app1", fp.name]
        self.assertIsNone(main())
        with open(fp.name, "r") as f:
            log = f.read().strip().split("\n")
            self.assertEqual(18, len(log))
            self.assertEqual("app1_run", log[0])
            self.assertEqual("app1_param=app1_param_value", log[1])
            self.assertEqual("solution1_app1_run", log[2])
            self.assertEqual("solution1_app1_close", log[3])
            self.assertEqual("solution2_app1_run", log[4])
            self.assertEqual("solution2_app1_close", log[5])
            self.assertEqual("app1_close", log[6])
            self.assertEqual("solution3_noparent_run", log[7])
            self.assertEqual("solution3_noparent_close", log[8])
            self.assertEqual("app2_run", log[9])
            self.assertEqual("app2_param=app2_param_value", log[10])
            self.assertEqual("solution4_app2_run", log[11])
            self.assertEqual("solution4_app2_close", log[12])
            self.assertEqual("solution5_app2_run", log[13])
            self.assertEqual("solution5_app2_close", log[14])
            self.assertEqual("app2_close", log[15])
            self.assertEqual("solution3_noparent_run", log[16])
            self.assertEqual("solution3_noparent_close", log[17])
            self.assertIsNone(hips.get_active_hips())

    # def test_deploy(self):
    #     sys.argv = ["", "deploy", get_dummy_solution_path()]
    #     self.assertIsNone(cmdline.main())

    def test_tutorial(self):
        sys.argv = ["", "tutorial", get_test_solution_path()]
        self.assertIsNone(main())

    # def test_repl(self):
    #     sys.argv = ["", "repl", get_dummy_solution_path()]
    #     self.assertIsNone(cmdline.main())

    def test_containerize(self):
        sys.argv = ["", "containerize", get_test_solution_path()]
        self.assertIsNone(main())

    def test_remove(self):
        sys.argv = ["", "remove", get_test_solution_path()]
        self.assertIsNone(main())

    def __resolve_hips(self, hips_dependency):
        path = get_test_solution_path(hips_dependency['name'] + ".py")
        return {"path": path}

    def __set_environment_name(self, hips_dependency):
        hips_dependency['_environment_name'] = 'hips'


def get_test_solution_path(solution_file="solution0_dummy.py"):
    current_path = Path(os.path.dirname(os.path.realpath(__file__)))
    path = current_path.joinpath("..", "resources", solution_file)
    return str(path.resolve())


def configure_test_logging(stream_handler):
    logger = logging.getLogger("test")

    if not logger.hasHandlers():
        logger.setLevel('INFO')
        ch = logging.StreamHandler(stream_handler)
        ch.setLevel('INFO')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        push_active_logger(logger)
    return logger


if __name__ == '__main__':
    unittest.main()

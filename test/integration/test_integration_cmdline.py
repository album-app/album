import logging
import os
import sys
import tempfile
import unittest.mock
from io import StringIO
from pathlib import Path
from unittest.mock import PropertyMock
from unittest.mock import patch

import hips.core as hips
from hips.cmdline import main
from hips.core.model.catalog_configuration import HipsCatalogCollection
from hips.core.model.environment import Environment
from hips.core.utils.conda import Conda
from hips_runner.logging import push_active_logger


# ToDo: CREATE AN INSTALL INTEGRATIONTEST

class TestHIPSCommandLine(unittest.TestCase):
    test_config = """catalogs:
    - https://gitlab.com/ida-mdc/hips-catalog.git
    """

    def setUp(self):
        # make sure no active hips are somehow configured!
        while hips.get_active_hips() is not None:
            hips.pop_active_hips()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.closed_tmp_file = tempfile.NamedTemporaryFile(delete=False)
        self.closed_tmp_file.close()

    def tearDown(self) -> None:
        # clean all environments specified in test-resources
        for e in ["app1", "app2", "solution3_noparent"]:
            if Conda.environment_exists(e):
                Conda.remove_environment(e)

        Path(self.closed_tmp_file.name).unlink()
        self.tmp_dir.cleanup()

    # ### CONTAINERIZE ###

    def test_containerize(self):
        sys.argv = ["", "containerize", get_test_solution_path()]
        self.assertIsNone(main())

    # ### DEPLOY ###

    # def test_deploy(self):
    #     sys.argv = ["", "deploy", get_dummy_solution_path()]
    #     self.assertIsNone(cmdline.main())

    # ### INSTALL ###

    def test_install(self):
        self.test_config += "- " + self.tmp_dir.name
        with open(self.closed_tmp_file.name, mode="w") as f:
            f.writelines(self.test_config)

        HipsCatalogCollection.instance = None  # lever out concept
        config = HipsCatalogCollection(self.closed_tmp_file.name)

        self.assertEqual(len(config.local_catalog), 0)

        sys.argv = ["", "install", str(get_test_solution_path())]

        with patch('hips.core.controller.install_manager.InstallManager.catalog_configuration',
                   new_callable=PropertyMock) as p_mock:
            p_mock.return_value = config
            self.assertIsNone(main())

        self.assertEqual(len(config.local_catalog), 1)

    @unittest.skip("Needs to be implemented!")
    def test_install_with_dependencies(self):
        # ToDo: implement
        pass

    def test_install_no_solution(self):
        sys.argv = ["", "install"]
        with self.assertRaises(SystemExit) as e:
            main()
        self.assertEqual(SystemExit(2).code, e.exception.code)

    # ### REMOVE ###

    @patch('hips.core.controller.remove_manager.shutil.rmtree')
    @patch('hips.core.controller.remove_manager.HipsCatalogCollection.resolve_from_str')
    @patch('hips.cmdline.__retrieve_logger')
    def test_remove(self, logger_mock, res_from_str_mock, rmtree_mock):
        captured_output = StringIO()
        logger_mock.side_effect = [configure_test_logging(captured_output)]

        self.test_config += "- " + self.tmp_dir.name
        with open(self.closed_tmp_file.name, "w") as f:
            f.writelines(self.test_config)

        # temporary catalog from a temporary config
        HipsCatalogCollection.instance = None  # lever out concept
        config = HipsCatalogCollection(self.closed_tmp_file.name)

        # resolving should return the relative path to the solution0_dummy resource file
        res_from_str_mock.return_value = {
            "path": get_test_solution_path("solution0_dummy_no_doi.py"), "catalog": config.local_catalog
        }

        self.assertEqual(len(config.local_catalog), 0)
        # manually add the solution0_dummy to the tmp-index
        config.local_catalog.catalog_index.update({
            "group": "group",
            "name": "name",
            "version": "0.1.0",
        })
        self.assertEqual(len(config.local_catalog), 1)

        sys.argv = ["", "remove", get_test_solution_path()]

        # overwrite the catalog_configuration attribute from the HipsRemover object to take our fake config
        with patch('hips.core.controller.remove_manager.RemoveManager.catalog_configuration',
                   new_callable=PropertyMock) as p_mock:
            p_mock.return_value = config
            self.assertIsNone(main())

        # assert that solution is removed from the catalog
        self.assertIn("Removed name", captured_output.getvalue())
        self.assertEqual(0, len(config.local_catalog))

        # assert that the correct path is deleted
        rmtree_mock.assert_called_once_with(
            config.configuration.cache_path_solution.joinpath("local", "group", "name", "0.1.0"),
            ignore_errors=True
        )

    def test_remove_solution_not_installed(self):
        sys.argv = ["", "remove", get_test_solution_path()]

        with self.assertRaises(IndexError) as context:
            main()
            self.assertIn("WARNING - Solution points to a local file", str(context.exception))

    # ### REPL ###

    # def test_repl(self):
    #     sys.argv = ["", "repl", get_dummy_solution_path()]
    #     self.assertIsNone(cmdline.main())

    # ### RUN ###

    @patch('hips.core.controller.run_manager.HipsCatalogCollection.resolve_from_str')
    def test_run(self, res_from_str_mock):
        # create test environment
        Environment(None, "unusedCacheName", "unusedCachePath").install()

        sys.argv = ["", "run", get_test_solution_path()]

        res_from_str_mock.side_effect = [{"path": get_test_solution_path(), "catalog": "aCatalog"}]

        self.assertIsNone(main())
        self.assertIsNone(hips.get_active_hips())

    @patch('hips.core.controller.run_manager.HipsCatalogCollection.resolve_from_str')
    @patch('hips.core.controller.run_manager.HipsCatalogCollection.resolve_hips_dependency')
    def test_run_with_parent(self, resolve_mock, res_from_str_mock):
        # create test environment
        Environment(None, "unusedCacheName", "unusedCachePath").install()

        # create app environment
        Environment({'environment_name': "app1"}, "unusedCacheName", "unusedCachePath").install()

        resolve_mock.side_effect = self.__resolve_hips
        res_from_str_mock.side_effect = [{"path": get_test_solution_path("solution1_app1.py"), "catalog": "aCatalog"}]

        fp = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        sys.argv = ["", "run", get_test_solution_path("solution1_app1.py"), "--file", fp.name, "--file_solution1_app1",
                    fp.name, "--app1_param", "value1"]
        self.assertIsNone(main())
        fp.close()
        with open(fp.name, "r") as f:
            log = f.read().strip().split("\n")
            self.assertEqual(5, len(log))
            self.assertEqual("app1_run", log[0])
            self.assertEqual("app1_param=value1", log[1])
            self.assertEqual("solution1_app1_run", log[2])
            self.assertEqual("solution1_app1_close", log[3])
            self.assertEqual("app1_close", log[4])
            self.assertIsNone(hips.get_active_hips())

    @patch('hips.core.controller.run_manager.HipsCatalogCollection.resolve_from_str')
    @patch('hips.core.controller.run_manager.HipsCatalogCollection.resolve_hips_dependency')
    def test_run_with_steps(self, run_resolve_mock, res_from_str_mock):
        # create test environment
        Environment(None, "unusedCacheName", "unusedCachePath").install()

        # create app environment
        Environment({'environment_name': "app1"}, "unusedCacheName", "unusedCachePath").install()

        # create solution3_noparent environment
        Environment({'environment_name': "solution3_noparent"}, "unusedCacheName", "unusedCachePath").install()

        run_resolve_mock.side_effect = self.__resolve_hips
        res_from_str_mock.side_effect = [{"path": get_test_solution_path("hips_with_steps.py"), "catalog": "aCatalog"}]

        fp = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        sys.argv = ["", "run", get_test_solution_path("hips_with_steps.py"), "--file", fp.name, "--file_solution1_app1",
                    fp.name]
        self.assertIsNone(main())
        fp.close()
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

    @patch('hips.core.controller.run_manager.HipsCatalogCollection.resolve_from_str')
    @patch('hips.core.controller.run_manager.HipsCatalogCollection.resolve_hips_dependency')
    def test_run_with_grouped_steps(self, run_resolve_mock, res_from_str_mock):
        # create test environment
        Environment(None, "unusedCacheName", "unusedCachePath").install()

        # create app environment
        Environment({'environment_name': "app1"}, "unusedCacheName", "unusedCachePath").install()
        Environment({'environment_name': "app2"}, "unusedCacheName", "unusedCachePath").install()

        # create solution3_noparent environment
        Environment({'environment_name': "solution3_noparent"}, "unusedCacheName", "unusedCachePath").install()

        run_resolve_mock.side_effect = self.__resolve_hips
        res_from_str_mock.side_effect = [
            {"path": get_test_solution_path("hips_with_steps_grouped.py"), "catalog": "aCatalog"}
        ]

        fp = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        sys.argv = ["", "run", get_test_solution_path("hips_with_steps_grouped.py"), "--file", fp.name,
                    "--file_solution1_app1", fp.name]
        self.assertIsNone(main())
        fp.close()
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

    # ### SEARCH ###

    def test_search_no_keyword(self):
        sys.argv = ["", "search"]
        with self.assertRaises(SystemExit) as e:
            main()
        self.assertEqual(SystemExit(2).code, e.exception.code)

    def test_search_emtpy_index(self):
        sys.argv = ["", "search", "keyword"]
        self.assertIsNone(main())

    @patch('hips.core.controller.search_manager.HipsCatalogCollection.get_search_index')
    @patch('hips.cmdline.__retrieve_logger')
    def test_search_filled_index(self, logger_mock, get_search_index_mock):
        # configure additional log output for checking
        captured_output = StringIO()
        logger_mock.side_effect = [configure_test_logging(captured_output)]

        self.test_config += "- " + str(Path(get_test_solution_path("")).joinpath("catalog_local"))
        with open(self.closed_tmp_file.name, mode="w") as f:
            f.writelines(self.test_config)

        # use config in test resources with relative path to a local catalog
        HipsCatalogCollection.instance = None  # lever out concept
        config = HipsCatalogCollection(self.closed_tmp_file.name)
        get_search_index_mock.return_value = {
            config.local_catalog.id: config.local_catalog.catalog_index.get_leaves_dict_list()
        }

        # define and run search
        sys.argv = ["", "search", "keyword1"]
        self.assertIsNone(main())

        # check output to have found the solution behind keyword1
        self.assertIn('catalog_local_ida-mdc_solution0_dummy_0.1.0', captured_output.getvalue())

    # ### TUTORIAL ###

    def test_tutorial(self):
        sys.argv = ["", "tutorial", get_test_solution_path()]
        self.assertIsNone(main())

    # ### ADD AND REMOVE CATALOG ###

    def test_add_remove_catalog(self):
        catalog_configuration = HipsCatalogCollection()
        self.assertIsNotNone(catalog_configuration)
        initial_catalogs = catalog_configuration.config_file_dict["catalogs"]
        self.assertIsNotNone(initial_catalogs)
        initial_len = len(initial_catalogs)
        somedir = "/tmp/somedir"
        sys.argv = ["", "add-catalog", somedir]
        self.assertIsNone(main())
        catalogs = HipsCatalogCollection().config_file_dict["catalogs"]
        self.assertEqual(initial_len + 1, len(catalogs))
        self.assertEqual(somedir, catalogs[len(catalogs) - 1])
        sys.argv = ["", "remove-catalog", somedir]
        self.assertIsNone(main())
        catalogs = HipsCatalogCollection().config_file_dict["catalogs"]
        self.assertEqual(initial_catalogs, catalogs)

    @staticmethod
    def __resolve_hips(hips_dependency, download=False):
        path = get_test_solution_path(hips_dependency['name'] + ".py")
        return {"path": path}


def get_test_solution_path(solution_file="solution0_dummy.py"):
    current_path = Path(os.path.dirname(os.path.realpath(__file__)))
    path = current_path.joinpath("..", "resources", solution_file)
    return str(path.resolve())


def configure_test_logging(stream_handler):
    logger = logging.getLogger("test")

    for handler in logger.handlers:
        logger.removeHandler(handler)

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

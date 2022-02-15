import unittest
import urllib.parse
from pathlib import Path
from time import time, sleep
from unittest.mock import patch

import flask_unittest

from album.core.controller.task_manager import TaskManager
from album.core.model.default_values import DefaultValues
from album.core.model.task import Task
from album.runner import album_logging
from album.runner.album_logging import LogLevel
from album.runner.core.model.coordinates import Coordinates
from album.server import AlbumServer
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationServer(flask_unittest.ClientTestCase, TestIntegrationCommon):
    port = 7896

    server = AlbumServer(port)
    app = server.init_server({'TESTING': True})

    def setUp(self, client) -> None:
        TestIntegrationCommon.setUp(self)
        self.init_collection()
        self.server.setup(self.album())
        flask_unittest.ClientTestCase.setUp(self, client)

    def tearDown(self, client) -> None:
        flask_unittest.ClientTestCase.tearDown(self, client)
        TestIntegrationCommon.tearDown(self)

    def test_server(self, client):
        # setting up test
        album_logging.set_loglevel(LogLevel.INFO)

        # check index route
        res_index = client.get("/index")
        self.assertEqual(200, res_index.status_code)

        # check catalogs route
        res_catalogs = client.get("/catalogs")
        self.assertEqual(200, res_catalogs.status_code)

        # check config route
        res_config = client.get("/config")
        self.assertEqual(200, res_config.status_code)

        # add remote catalog
        remote_catalog = "https://gitlab.com/album-app/catalogs/templates/catalog"
        self.assertCatalogPresence(self.album_controller().catalogs().get_all(), remote_catalog, False)
        res_add_catalog = client.get("/add-catalog?src=" + urllib.parse.quote(remote_catalog))
        self.assertEqual(200, res_add_catalog.status_code)
        self.assertCatalogPresence(self.album_controller().catalogs().get_all(), remote_catalog, True)

        # remove remote catalog
        res_remove_catalog = client.get("/remove-catalog?src=" + urllib.parse.quote(remote_catalog))
        self.assertEqual(200, res_remove_catalog.status_code)
        self.assertCatalogPresence(self.album_controller().catalogs().get_all(), remote_catalog, False)

        # clone catalog template
        local_catalog_name = "mycatalog"
        local_catalogs_path = Path(self.tmp_dir.name).joinpath("my-catalogs")
        local_catalogs = str(local_catalogs_path)
        local_catalog_path = local_catalogs_path.joinpath(local_catalog_name)
        self.assertCatalogPresence(self.album_controller().catalogs().get_all(), local_catalogs, False)

        res_clone_catalog = client.get(
            f"/clone/template:catalog?target_dir={urllib.parse.quote(local_catalogs)}&name={local_catalog_name}"
        )
        self.assertEqual(200, res_clone_catalog.status_code)
        self._finish_taskmanager_with_timeout(self.server._task_manager, 30)
        self.assertCatalogPresence(
            self.album_controller().catalogs().get_all(), local_catalog_path, False
        )
        self.assertTrue(local_catalogs_path.exists())
        self.assertTrue(local_catalog_path.exists())
        self.assertTrue(local_catalog_path.joinpath(DefaultValues.catalog_index_metafile_json.value).exists())

        # add catalog
        res_add_catalog = client.get("/add-catalog?src=" + urllib.parse.quote(str(local_catalog_path)))
        self.assertEqual(200, res_add_catalog.status_code)
        catalog_id = res_add_catalog.json["catalog_id"]
        self.assertCatalogPresence(
            self.album_controller().catalogs().get_all(), str(local_catalog_path), True
        )

        # clone solution
        group = "group"
        name = "solution7_long_routines"
        version = "0.1.0"
        clone_src = self.get_test_solution_path(f"{name}.py")
        solution_target_dir = Path(self.tmp_dir.name).joinpath("my-solutions")
        solution_target_name = "my-" + name
        solution_target_file = solution_target_dir.joinpath(
            solution_target_name,
            DefaultValues.solution_default_name.value
        )

        # assert that cloned solution not installed
        res_status = client.get(f'/status/{local_catalog_name}/{group}/{name}/{version}')
        self.assertEqual(404, res_status.status_code)

        res_clone_solution = client.get(
            f"/clone?path={clone_src}&target_dir"
            f"={urllib.parse.quote(str(solution_target_dir))}&name={solution_target_name}"
        )
        self.assertEqual(200, res_clone_solution.status_code)
        self._finish_taskmanager_with_timeout(self.server._task_manager, 30)

        self.assertTrue(solution_target_dir.exists())
        self.assertTrue(solution_target_dir.joinpath(solution_target_name).exists())
        self.assertTrue(solution_target_file.exists())

        # deploy solution to catalog
        path_to_solution = urllib.parse.quote(str(solution_target_file))
        res_deploy = client.get(f"/deploy?path={path_to_solution}&catalog_name={local_catalog_name}")
        self.assertEqual(200, res_deploy.status_code)
        self.assertIsNotNone(res_deploy.json)
        self.assertIsNotNone(res_deploy.json["id"])

        self._finish_taskmanager_with_timeout(self.server._task_manager, 30)

        # update catalog cache
        res_update_catalog = client.get("/update?src=" + urllib.parse.quote(str(local_catalog_path)))
        self.assertEqual(200, res_update_catalog.status_code)

        # upgrade collection
        res_update_catalog = client.get("/upgrade?src=" + urllib.parse.quote((str(local_catalog_path))))
        self.assertEqual(200, res_update_catalog.status_code)

        # check that solution exists, but is not installed
        res_status = client.get(f'/status/{local_catalog_name}/{group}/{name}/{version}')
        self.assertEqual(200, res_status.status_code)
        self.assertIsNotNone(res_status.json)
        self.assertFalse(res_status.json["installed"])

        # install solution
        res_install = client.get(f'/install/{local_catalog_name}/{group}/{name}/{version}')
        self.assertEqual(200, res_install.status_code)
        self.assertIsNotNone(res_install.json)
        self.assertIsNotNone(res_deploy.json["id"])

        self._finish_taskmanager_with_timeout(self.server._task_manager, 600)

        # check that solution is installed
        self.assertTrue(self.album_controller().collection_manager().get_collection_index().is_installed(
            catalog_id, Coordinates(group, name, version)))
        res_status = client.get(f'/status/{local_catalog_name}/{group}/{name}/{version}')
        self.assertEqual(200, res_status.status_code)
        self.assertIsNotNone(res_status.json)
        self.assertTrue(res_status.json["installed"])

        # trigger running and testing the solution simultaneously
        res_run = client.get(f'/run/{local_catalog_name}/{group}/{name}/{version}?testArg1=something')
        res_test = client.get(f'/test/{local_catalog_name}/{group}/{name}/{version}')

        # check status of ongoing tasks
        self.assertEqual(200, res_run.status_code)
        self.assertEqual(200, res_test.status_code)

        self.assertIsNotNone(res_run.json)
        self.assertIsNotNone(res_test.json)

        task_run_id = res_run.json["id"]
        task_test_id = res_test.json["id"]

        self.assertIsNotNone(task_run_id)
        self.assertIsNotNone(task_test_id)

        self.assertTrue(self.server._task_manager.server_queue.unfinished_tasks)

        res_status = client.get(f'/status/{task_run_id}')
        self.assertEqual(200, res_status.status_code)
        self.assertIsNotNone(res_status.json)

        # wait for completion of tasks
        self._finish_taskmanager_with_timeout(self.server._task_manager, 30)

        res_status = client.get(f'/status/{task_run_id}')
        self.assertEqual(200, res_status.status_code)
        self.assertIsNotNone(res_status.json)

        self.assertEqual(Task.Status.FINISHED, self.server._task_manager.get_task(task_run_id).status())
        self.assertEqual(Task.Status.FINISHED, self.server._task_manager.get_task(task_test_id).status())

        # check that tasks were executed properly
        run_logs = self.server._task_manager.get_task(task_run_id).log_handler()
        test_logs = self.server._task_manager.get_task(task_test_id).log_handler()
        self.assertIsNotNone(run_logs)
        self.assertIsNotNone(test_logs)
        self.assertTrue(len(run_logs.records()) > 0)
        self.assertTrue(len(test_logs.records()) > 0)
        self.assertTrue(self.includes_msg(run_logs.records(), "solution7_long_routines_run_start"))
        self.assertTrue(self.includes_msg(run_logs.records(), "solution7_long_routines_run_end"))
        self.assertTrue(self.includes_msg(test_logs.records(), "solution7_long_routines_test_start"))
        self.assertTrue(self.includes_msg(test_logs.records(), "solution7_long_routines_test_end"))

        # test recently launched and installed solutions
        res_recently_installed = client.get("/recently-installed")
        self.assertEqual(200, res_recently_installed.status_code)
        res_recently_launched = client.get("/recently-launched")
        self.assertEqual(200, res_recently_launched.status_code)

        # check index route again
        res_index = client.get("/index")
        self.assertEqual(200, res_index.status_code)

        # remove solution
        res_uninstall = client.get(f'/uninstall/{local_catalog_name}/{group}/{name}/{version}')
        self.assertEqual(200, res_uninstall.status_code)
        self._finish_taskmanager_with_timeout(self.server._task_manager, 600)

        # remove catalog
        res_status = client.get("/remove-catalog?src=" + urllib.parse.quote((str(local_catalog_path))))
        self.assertEqual(200, res_status.status_code)
        self.assertCatalogPresence(self.album_controller().catalogs().get_all(), local_catalog_path,
                                   False)

        # check that solution is not accessible any more
        res_status = client.get(f'/status/{local_catalog_name}/{group}/{name}/{version}')
        self.assertEqual(404, res_status.status_code)

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_server_add_solution(self, client, get_environment_path):
        get_environment_path.return_value = self.album_instance._controller.environment_manager().get_conda_manager().get_active_environment_path()
        solution_path = self.get_test_solution_path("solution9_throws_exception.py")
        solution = self.fake_install(solution_path, create_environment=False)

        res_run = client.get(f"/run/{solution.coordinates().group()}/{solution.coordinates().name()}/{solution.coordinates().version()}")
        self.assertEqual(200, res_run.status_code)
        self.assertIsNotNone(res_run.json)
        task_run_id = res_run.json["id"]
        self.assertEqual("0", task_run_id)

        # wait for completion of tasks
        self._finish_taskmanager_with_timeout(self.server._task_manager, 30)

        self.assertEqual(Task.Status.FAILED, self.server._task_manager.get_task(task_run_id).status())
        res_status = client.get(f'/status/{task_run_id}')
        self.assertEqual(200, res_status.status_code)
        self.assertIsNotNone(res_status.json)
        self.assertEqual("FAILED", res_status.json["status"])

    def _finish_taskmanager_with_timeout(self, task_manager: TaskManager, timeout):
        # since queue.join has no timeout, we are doing something else to check if the queue is processed
        # self.server.task_manager.server_queue.join()
        stop = time() + timeout
        while task_manager.server_queue.unfinished_tasks and time() < stop:
            sleep(1)
        # make sure tasks are finished
        self.assertFalse(task_manager.server_queue.unfinished_tasks)

    @staticmethod
    def includes_msg(records, msg):
        for record in records:
            # print(record.msg)
            if msg in record.msg:
                return True
        return False

    def assertCatalogPresence(self, catalogs, src, should_be_present):
        present = False
        for catalog in catalogs:
            if str(catalog.src()) == src:
                present = True
        self.assertEqual(should_be_present, present)


if __name__ == '__main__':
    unittest.main()

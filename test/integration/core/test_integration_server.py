import unittest
import urllib.parse
from pathlib import Path
from time import time, sleep

import flask_unittest

from album.core.controller.catalog_handler import CatalogHandler
from album.core.controller.task_manager import TaskManager
from album.core.model.group_name_version import GroupNameVersion
from album.core.model.task import Task
from album.core.server import AlbumServer
from album_runner import logging
from album_runner.logging import LogLevel
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationServer(flask_unittest.ClientTestCase, TestIntegrationCommon):

    port = 7896

    server = AlbumServer(port)
    app = server.init_server({'TESTING': True})

    def setUp(self, client) -> None:
        self.server.setup(self.port)
        TestIntegrationCommon.setUp(self)
        flask_unittest.ClientTestCase.setUp(self, client)

    def tearDown(self, client) -> None:
        flask_unittest.ClientTestCase.tearDown(self, client)
        TestIntegrationCommon.tearDown(self)

    def test_server(self, client):

        # setting up test
        logging.set_loglevel(LogLevel.INFO)

        # add remote catalog

        remote_catalog = "https://gitlab.com/album-app/catalogs/templates/catalog"
        self.assertCatalogPresence(self.collection_manager.catalogs().get_all(), remote_catalog, False)
        res_add_catalog = client.get("/add-catalog?src=" + urllib.parse.quote(remote_catalog))
        self.assertEqual(200, res_add_catalog.status_code)
        self.assertCatalogPresence(self.collection_manager.catalogs().get_all(), remote_catalog, True)

        # remove remote catalog

        res_remove_catalog = client.get("/remove-catalog?src=" + urllib.parse.quote(remote_catalog))
        self.assertEqual(200, res_remove_catalog.status_code)
        self.assertCatalogPresence(self.collection_manager.catalogs().get_all(), remote_catalog, False)

        # add local catalog

        local_catalog_name = "mycatalog"
        local_catalog_path = Path(self.tmp_dir.name).joinpath(local_catalog_name)
        CatalogHandler.create_new_catalog(local_catalog_path, local_catalog_name)
        local_catalog = str(local_catalog_path)
        self.assertCatalogPresence(self.collection_manager.catalogs().get_all(), local_catalog, False)
        res_add_catalog = client.get("/add-catalog?src=" + urllib.parse.quote(local_catalog))
        self.assertEqual(200, res_add_catalog.status_code)
        self.assertCatalogPresence(self.collection_manager.catalogs().get_all(), local_catalog, True)

        # deploy, install, and run solution

        group = "group"
        name = "solution7_long_routines"
        version = "0.1.0"

        # assert that it's not installed
        res_status = client.get(f'/status/{local_catalog_name}/{group}/{name}/{version}')
        self.assertEqual(404, res_status.status_code)

        # deploy solution to catalog

        path_to_solution = urllib.parse.quote(self.get_test_solution_path(f"{name}.py"))
        res_deploy = client.get(f"/deploy?path={path_to_solution}&catalog_name={local_catalog_name}")
        self.assertEqual(200, res_deploy.status_code)
        self.assertIsNotNone(res_deploy.json)
        task_deploy_id = res_deploy.json["id"]
        self.assertEqual("0", task_deploy_id)

        task_manager = TaskManager()
        self._finish_taskmanager_with_timeout(task_manager, 30)

        # TODO we need the solution deployed to the catalog to be added to our local collection.
        #  in the future, this should work:
        # res_update_catalog = client.get("/update-catalog?src=" + urllib.parse.quote(local_catalog))
        # self.assertEqual(200, res_update_catalog.status_code)
        # TODO .. for now, we just remove and add the catalog again:
        res_add_catalog = client.get("/remove-catalog?src=" + urllib.parse.quote(local_catalog))
        self.assertEqual(200, res_add_catalog.status_code)
        res_add_catalog = client.get("/add-catalog?src=" + urllib.parse.quote(local_catalog))
        self.assertEqual(200, res_add_catalog.status_code)
        self.assertIsNotNone(res_add_catalog.json)
        catalog_id = res_add_catalog.json["catalog_id"]

        # check that solution exists, but is not installed

        res_status = client.get(f'/status/{local_catalog_name}/{group}/{name}/{version}')
        self.assertEqual(200, res_status.status_code)
        self.assertIsNotNone(res_status.json)
        self.assertFalse(res_status.json["installed"])

        # install solution

        res_install = client.get(f'/install/{local_catalog_name}/{group}/{name}/{version}')
        self.assertEqual(200, res_install.status_code)
        self.assertIsNotNone(res_install.json)
        task_install_id = res_install.json["id"]
        self.assertEqual("1", task_install_id)

        self._finish_taskmanager_with_timeout(task_manager, 60)

        # check that solution is installed
        self.assertTrue(self.collection_manager.catalog_collection.is_installed(catalog_id, GroupNameVersion(group, name, version)))
        res_status = client.get(f'/status/{local_catalog_name}/{group}/{name}/{version}')
        self.assertEqual(200, res_status.status_code)
        self.assertIsNotNone(res_status.json)
        self.assertTrue(res_status.json["installed"])

        # trigger running and testing the solution simultaneously

        res_run = client.get(f'/run/{local_catalog_name}/{group}/{name}/{version}')
        res_test = client.get(f'/test/{local_catalog_name}/{group}/{name}/{version}')

        # check status of ongoing tasks

        self.assertEqual(200, res_run.status_code)
        self.assertEqual(200, res_test.status_code)

        self.assertIsNotNone(res_run.json)
        self.assertIsNotNone(res_test.json)

        task_run_id = res_run.json["id"]
        task_test_id = res_test.json["id"]

        self.assertEqual("2", task_run_id)
        self.assertEqual("3", task_test_id)

        self.assertTrue(task_manager.server_queue.unfinished_tasks)

        # wait for completion of tasks
        self._finish_taskmanager_with_timeout(task_manager, 30)

        self.assertEqual(Task.Status.FINISHED, task_manager.get_task(task_run_id).status)
        self.assertEqual(Task.Status.FINISHED, task_manager.get_task(task_test_id).status)

        # check that tasks were executed properly

        run_logs = task_manager.get_task(task_run_id).log_handler
        test_logs = task_manager.get_task(task_test_id).log_handler
        self.assertIsNotNone(run_logs)
        self.assertIsNotNone(test_logs)
        self.assertTrue(len(run_logs.records) > 0)
        self.assertTrue(len(test_logs.records) > 0)
        self.assertTrue(self.includes_msg(run_logs.records, "solution7_long_routines_run_start"))
        self.assertTrue(self.includes_msg(run_logs.records, "solution7_long_routines_run_end"))
        self.assertTrue(self.includes_msg(test_logs.records, "solution7_long_routines_test_start"))
        self.assertTrue(self.includes_msg(test_logs.records, "solution7_long_routines_test_end"))

        # remove catalog
        res_status = client.get("/remove-catalog?src=" + urllib.parse.quote(local_catalog))
        self.assertEqual(200, res_status.status_code)
        self.assertCatalogPresence(self.collection_manager.catalogs().get_all(), remote_catalog, False)

        # check that solution is not accessible any more
        res_status = client.get(f'/status/{local_catalog_name}/{group}/{name}/{version}')
        self.assertEqual(404, res_status.status_code)

    def _finish_taskmanager_with_timeout(self, task_manager, timeout):
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
            print(record.msg)
            if msg in record.msg:
                return True
        return False

    def assertCatalogPresence(self, catalogs, src, should_be_present):
        present = False
        for catalog in catalogs:
            if str(catalog.src) == src:
                present = True
        self.assertEqual(should_be_present, present)


if __name__ == '__main__':
    unittest.main()

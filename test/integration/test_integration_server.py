import unittest
from time import time, sleep

import flask_unittest

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

        # sanity checks
        self.assertEqual(self.test_solution_db.instance, self.server.solutions_db.instance)

        # setting up test

        logging.set_loglevel(LogLevel.INFO)

        catalog = self.test_catalog_collection.local_catalog.id
        group = "group"
        name = "solution7_long_routines"
        version = "0.1.0"

        # check that solution is not installed

        res_status = client.get(f'/status/{catalog}/{group}/{name}/{version}')
        self.assertEqual(200, res_status.status_code)
        self.assertIsNotNone(res_status.json)
        self.assertFalse(res_status.json["installed"])

        # install solution

        path = self.get_test_solution_path("solution7_long_routines.py")
        self.fake_install(path)

        # check that solution is installed

        self.assertTrue(self.server.solutions_db.is_installed(catalog, group, name, version))
        res_status = client.get(f'/status/{catalog}/{group}/{name}/{version}')
        self.assertEqual(200, res_status.status_code)
        self.assertIsNotNone(res_status.json)
        self.assertTrue(res_status.json["installed"])

        # trigger running and testing the solution simultaneously

        res_run = client.get(f'/run/{catalog}/{group}/{name}/{version}')
        res_test = client.get(f'/test/{catalog}/{group}/{name}/{version}')

        # check status of ongoing tasks

        self.assertEqual(200, res_run.status_code)
        self.assertEqual(200, res_test.status_code)

        self.assertIsNotNone(res_run.json)
        self.assertIsNotNone(res_test.json)

        task_run_id = res_run.json["id"]
        task_test_id = res_test.json["id"]

        self.assertEqual("0", task_run_id)
        self.assertEqual("1", task_test_id)

        self.assertTrue(self.server.task_manager.server_queue.unfinished_tasks)

        # wait for completion of tasks

        # since queue.join has no timeout, we are doing something else to check if the queue is processed
        # self.server.task_manager.server_queue.join()
        timeout = 30
        stop = time() + timeout
        while self.server.task_manager.server_queue.unfinished_tasks and time() < stop:
            sleep(1)

        # make sure tasks are finished

        self.assertFalse(self.server.task_manager.server_queue.unfinished_tasks)

        self.assertEqual(Task.Status.FINISHED, self.server.task_manager.get_task(task_run_id).status)
        self.assertEqual(Task.Status.FINISHED, self.server.task_manager.get_task(task_test_id).status)

        # check that tasks were executed properly

        run_logs = self.server.task_manager.get_task(task_run_id).log_handler
        test_logs = self.server.task_manager.get_task(task_test_id).log_handler
        self.assertIsNotNone(run_logs)
        self.assertIsNotNone(test_logs)
        self.assertTrue(len(run_logs.records) > 0)
        self.assertTrue(len(test_logs.records) > 0)
        self.assertTrue(self.includes_msg(run_logs.records, "solution7_long_routines_run_start"))
        self.assertTrue(self.includes_msg(run_logs.records, "solution7_long_routines_run_end"))
        self.assertTrue(self.includes_msg(test_logs.records, "solution7_long_routines_test_start"))
        self.assertTrue(self.includes_msg(test_logs.records, "solution7_long_routines_test_end"))

    @staticmethod
    def includes_msg(records, msg):
        for record in records:
            print(record.msg)
            if msg in record.msg:
                return True
        return False


if __name__ == '__main__':
    unittest.main()

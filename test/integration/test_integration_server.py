import unittest
from time import time, sleep
from unittest.mock import MagicMock

import flask_unittest

import album
import album.core as album
from album.core.model.environment import Environment
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
        TestIntegrationCommon.setUp(self)

    def tearDown(self, client) -> None:
        TestIntegrationCommon.tearDown(self)

    def test_server(self, client):

        logging.set_loglevel(LogLevel.INFO)

        test_env_name = self.test_catalog_collection.local_catalog.id + "_group_solution7_long_routines_0.1.0"
        Environment(None, test_env_name, "unusedCachePath").install()

        path = self.get_test_solution_path("solution7_long_routines.py")
        self.fake_install(path)
        a = album.load(path)

        _get_solution_path = MagicMock(return_value=path)
        self.server._get_solution_path = _get_solution_path

        resolve_from_str = MagicMock(return_value={"path": path, "catalog": self.test_catalog_collection.local_catalog})
        self.server.catalog_collection.resolve_from_str = resolve_from_str

        res_run = client.get(f'/run/{a["group"]}/{a["name"]}/{a["version"]}')
        res_test = client.get(f'/test/{a["group"]}/{a["name"]}/{a["version"]}')

        self.assertEqual(200, res_run.status_code)
        self.assertEqual(200, res_test.status_code)

        self.assertIsNotNone(res_run.json)
        self.assertIsNotNone(res_test.json)

        task_run_id = res_run.json["id"]
        task_test_id = res_test.json["id"]

        self.assertEqual("0", task_run_id)
        self.assertEqual("1", task_test_id)

        self.assertTrue(self.server.task_manager.server_queue.unfinished_tasks)

        # since queue.join has no timeout, we are doing something else to check if the queue is processed
        # self.server.task_manager.server_queue.join()
        timeout = 30
        stop = time() + timeout
        while self.server.task_manager.server_queue.unfinished_tasks and time() < stop:
            sleep(1)

        self.assertFalse(self.server.task_manager.server_queue.unfinished_tasks)

        self.assertEqual(Task.Status.FINISHED, self.server.task_manager.get_task(task_run_id).status)
        self.assertEqual(Task.Status.FINISHED, self.server.task_manager.get_task(task_test_id).status)

        self.assertEqual(2, _get_solution_path.call_count)
        self.assertEqual(2, resolve_from_str.call_count)

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

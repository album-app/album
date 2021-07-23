import unittest
from unittest.mock import MagicMock

import flask_unittest
from flask.testing import FlaskClient

from album.core.server import AlbumServer
from test.unit.test_unit_common import TestUnitCommon


class TestServer(flask_unittest.ClientTestCase, TestUnitCommon):

    port = 7896
    server = AlbumServer(port)
    app = server.init_server({'TESTING': True})

    def setUp(self, client: FlaskClient) -> None:
        TestUnitCommon.setUp(self)
        flask_unittest.ClientTestCase.setUp(self, client)

    def tearDown(self, client: FlaskClient) -> None:
        flask_unittest.ClientTestCase.tearDown(self, client)
        TestUnitCommon.tearDown(self)

    def getJSONResponse(self, client, path):
        response = client.get(path)
        self.assertEqual(200, response.status_code)
        return response.json

    def test_root(self, client):
        json = self.getJSONResponse(client, "/")
        self.assertIsNotNone(json)

    def test_run(self, client):
        route = MagicMock(return_value=None)
        self.server.run_manager.run = route
        self.__test_solution_route(client, "run", route)

    def test_install(self, client):
        route = MagicMock(return_value=None)
        self.server.install_manager.install = route
        self.__test_solution_route(client, "install", route)

    def test_remove(self, client):
        route = MagicMock(return_value=None)
        self.server.remove_manager.remove = route
        self.__test_solution_route(client, "remove", route)

    def test_test(self, client):
        route = MagicMock(return_value=None)
        self.server.test_manager.test = route
        self.__test_solution_route(client, "test", route)

    def test_add_catalog(self, client):
        route = MagicMock(return_value=None)
        self.server.catalog_manager.add = route
        self.__test_catalog_route(client, "add-catalog", route)

    def test_remove_catalog(self, client):
        route = MagicMock(return_value=None)
        self.server.catalog_manager.remove = route
        self.__test_catalog_route(client, "remove-catalog", route)

    def test_search(self, client):
        route = MagicMock(return_value={})
        self.server.search_manager.search = route
        json = self.getJSONResponse(client, "/search/searchterm")
        self.assertIsNotNone(json)
        self.server.task_manager.server_queue.join()
        self.assertEqual(1, route.call_count)

    def __test_solution_route(self, client, route, route_mock):
        _get_solution_path = MagicMock(return_value="/my/solution/path.py")
        self.server._get_solution_path = _get_solution_path
        json = self.getJSONResponse(client, "/%s/catalog/group/name/version" % route)
        self.assertIsNotNone(json)
        self.server.task_manager.server_queue.join()
        self.assertEqual(1, route_mock.call_count)
        json = self.getJSONResponse(client, "/%s/group/name/version" % route)
        self.assertIsNotNone(json)
        self.server.task_manager.server_queue.join()
        self.assertEqual(2, route_mock.call_count)

    def __test_catalog_route(self, client, route, route_mock):
        json = self.getJSONResponse(client, "/%s/CATALOG_URL" % route)
        self.assertIsNotNone(json)
        self.server.task_manager.server_queue.join()
        self.assertEqual(1, route_mock.call_count)


if __name__ == '__main__':
    unittest.main()

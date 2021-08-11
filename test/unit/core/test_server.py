import unittest
from unittest.mock import patch

import flask_unittest
from album.core.controller.task_manager import TaskManager
from flask.testing import FlaskClient

from album.core.model.catalog import Catalog
from album.core.server import AlbumServer
from test.unit.test_unit_common import TestUnitCommon


class TestServer(flask_unittest.ClientTestCase, TestUnitCommon):

    port = 7896
    server = AlbumServer(port)
    app = server.init_server({'TESTING': True})

    def setUp(self, client: FlaskClient) -> None:
        TestUnitCommon.setUp(self)
        self.create_test_config()
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

    @patch("album.core.controller.run_manager.RunManager.run", return_value=None)
    def test_run(self, client, route):
        self.__test_solution_route(client, "run", route)

    @patch("album.core.controller.install_manager.InstallManager.install", return_value=None)
    def test_install(self, client, route):
        self.__test_solution_route(client, "install", route)

    @patch("album.core.controller.remove_manager.RemoveManager.remove", return_value=None)
    def test_remove(self, client, route):
        self.__test_solution_route(client, "remove", route)

    @patch("album.core.controller.test_manager.TestManager.test", return_value=None)
    def test_test(self, client, route):
        self.__test_solution_route(client, "test", route)

    @patch("album.core.controller.catalog_manager.CatalogManager.add_catalog_to_collection", return_value=Catalog(1, "", ""))
    def test_add_catalog(self, client, route):
        json = self.getJSONResponse(client, "/%s?src=CATALOG_URL" % "add-catalog")
        self.assertIsNotNone(json)
        self.assertEqual(1, json["catalog_id"])
        self.assertEqual(3, route.call_count)

    @patch("album.core.controller.catalog_manager.CatalogManager.remove_catalog_from_collection_by_src", return_value=None)
    def test_remove_catalog(self, client, route):
        json = self.getJSONResponse(client, "/%s?src=CATALOG_URL" % "remove-catalog")
        self.assertIsNotNone(json)
        self.assertEqual(1, route.call_count)

    @patch("album.core.controller.search_manager.SearchManager.search", return_value={})
    def test_search(self, client, route):
        json = self.getJSONResponse(client, "/search/searchterm")
        self.assertIsNotNone(json)
        self.assertEqual(1, route.call_count)

    def __test_solution_route(self, client, route, route_mock):
        json = self.getJSONResponse(client, "/%s/catalog/group/name/version" % route)
        self.assertIsNotNone(json)
        TaskManager().server_queue.join()
        self.assertEqual(1, route_mock.call_count)
        json = self.getJSONResponse(client, "/%s/group/name/version" % route)
        self.assertIsNotNone(json)
        TaskManager().server_queue.join()
        self.assertEqual(2, route_mock.call_count)


if __name__ == '__main__':
    unittest.main()

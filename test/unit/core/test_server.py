import unittest
from unittest.mock import MagicMock

import flask_unittest

from album.core.server import AlbumServer


class TestServer(flask_unittest.ClientTestCase):

    port = 7896
    server = AlbumServer(port)
    app = server.init_server({'TESTING': True})

    def getJSONResponse(self, client, path):
        response = client.get(path)
        self.assertEquals(200, response.status_code)
        return response.json

    def test_root(self, client):
        json = self.getJSONResponse(client, "/")
        self.assertIsNotNone(json)

    def testRun(self, client):
        route = MagicMock(return_value=None)
        self.server.run_manager.run = route
        self.__testSolutionRoute(client, "run", route)

    def testInstall(self, client):
        route = MagicMock(return_value=None)
        self.server.install_manager.install = route
        self.__testSolutionRoute(client, "install", route)

    def testRemove(self, client):
        route = MagicMock(return_value=None)
        self.server.remove_manager.remove = route
        self.__testSolutionRoute(client, "remove", route)

    def testTest(self, client):
        route = MagicMock(return_value=None)
        self.server.test_manager.test = route
        self.__testSolutionRoute(client, "test", route)

    def testAddCatalog(self, client):
        route = MagicMock(return_value=None)
        self.server.catalog_manager.add = route
        self.__testCatalogRoute(client, "add-catalog", route)

    def testRemoveCatalog(self, client):
        route = MagicMock(return_value=None)
        self.server.catalog_manager.remove = route
        self.__testCatalogRoute(client, "remove-catalog", route)

    def testSearch(self, client):
        route = MagicMock(return_value=None)
        self.server.search_manager.search = route
        json = self.getJSONResponse(client, "/search/searchterm")
        self.assertIsNotNone(json)
        self.server.server_queue.join()
        self.assertEquals(1, route.call_count)

    def __testSolutionRoute(self, client, route, route_mock):
        _get_solution_path = MagicMock(return_value="/my/solution/path.py")
        self.server._get_solution_path = _get_solution_path
        json = self.getJSONResponse(client, "/catalog/group/name/version/%s" % route)
        self.assertIsNotNone(json)
        self.server.server_queue.join()
        self.assertEquals(1, route_mock.call_count)

    def __testCatalogRoute(self, client, route, route_mock):
        json = self.getJSONResponse(client, "/%s/CATALOG_URL" % route)
        self.assertIsNotNone(json)
        self.server.server_queue.join()
        self.assertEquals(1, route_mock.call_count)


if __name__ == '__main__':
    unittest.main()

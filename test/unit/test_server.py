import unittest
from unittest.mock import patch, MagicMock

import flask_unittest
from flask.testing import FlaskClient

from album.core.model.catalog import Catalog
from album.server import AlbumServer
from test.unit.test_unit_common import TestUnitCommon
from test.unit.test_unit_core_common import EmptyTestClass


@patch("album.core.controller.collection.catalog_handler.CatalogHandler._retrieve_catalog_meta_information",
       return_value={"name": "catalog_local", "version": "0.1.0"})
class TestServer(flask_unittest.ClientTestCase, TestUnitCommon):

    port = 7896
    server = AlbumServer(port)
    app = server.init_server({'TESTING': True})

    def setUp(self, client: FlaskClient) -> None:
        TestUnitCommon.setUp(self)
        album = self.create_album_test_instance()
        self.server.setup(album)
        flask_unittest.ClientTestCase.setUp(self, client)

    def tearDown(self, client: FlaskClient) -> None:
        flask_unittest.ClientTestCase.tearDown(self, client)
        TestUnitCommon.tearDown(self)

    def getJSONResponse(self, client, path):
        response = client.get(path)
        self.assertEqual(200, response.status_code)
        return response.json

    def test_root(self, client, _):
        json = self.getJSONResponse(client, "/")
        self.assertIsNotNone(json["version"])
        self.assertIsNotNone(json["author"])
        self.assertIsNotNone(json["email"])

    def test_index(self, client, _):
        json = self.getJSONResponse(client, "/index")
        self.assertIsNotNone(json["catalogs"])

    @patch("album.core.controller.run_manager.RunManager.run", return_value=None)
    def test_run(self, client, route, _):
        self.__test_solution_route(client, "run", route)

    @patch("album.core.controller.install_manager.InstallManager.install", return_value=None)
    def test_install(self, client, route, _):
        self.__test_solution_route(client, "install", route)

    @patch("album.core.controller.install_manager.InstallManager.uninstall", return_value=None)
    def test_uninstall(self, client, route, _):
        self.__test_solution_route(client, "uninstall", route)

    @patch("album.core.controller.test_manager.TestManager.test", return_value=None)
    def test_test(self, client, route, _):
        self.__test_solution_route(client, "test", route)

    @patch("album.core.controller.collection.collection_manager.CatalogHandler.add_by_src", return_value=Catalog(1, "", ""))
    def test_add_catalog(self, client, route, _):
        json = self.getJSONResponse(client, "/add-catalog?src=CATALOG_URL")
        self.assertIsNotNone(json)
        self.assertEqual(1, json["catalog_id"])
        self.assertEqual(1, route.call_count)

    @patch("album.core.controller.collection.collection_manager.CatalogHandler.remove_from_collection_by_src", return_value=None)
    def test_remove_catalog(self, client, route, _):
        json = self.getJSONResponse(client, "/remove-catalog?src=CATALOG_URL")
        self.assertIsNotNone(json)
        self.assertEqual(1, route.call_count)

    @patch("album.core.controller.clone_manager.CloneManager.clone", return_value=None)
    def test_clone_catalog(self, client, route, _):
        json = self.getJSONResponse(client, f"/clone/catalog?target_dir={self.tmp_dir.name}&name=my-name")
        self.assertIsNotNone(json)
        self.server.task_manager().finish_tasks()
        route.assert_called_once_with("catalog", self.tmp_dir.name, "my-name")

    @patch("album.core.controller.clone_manager.CloneManager.clone", return_value=None)
    def test_clone_solution(self, client, route, _):
        json = self.getJSONResponse(client, f"/clone/group/name/version?target_dir={self.tmp_dir.name}&name=my-name")
        self.assertIsNotNone(json)
        self.server.task_manager().finish_tasks()
        route.assert_called_once_with("group:name:version", self.tmp_dir.name, "my-name")

    @patch("album.core.controller.clone_manager.CloneManager.clone", return_value=None)
    def test_clone_solution_by_path(self, client, route, _):
        json = self.getJSONResponse(client, f"/clone?path=my-path&target_dir={self.tmp_dir.name}&name=my-name")
        self.assertIsNotNone(json)
        self.server.task_manager().finish_tasks()
        route.assert_called_once_with("my-path", self.tmp_dir.name, "my-name")

    @patch("album.core.controller.search_manager.SearchManager.search", return_value={})
    def test_search(self, client, route, _):
        json = self.getJSONResponse(client, "/search/searchterm")
        self.assertIsNotNone(json)
        self.assertEqual(1, route.call_count)

    def __test_solution_route(self, client, route, route_mock):
        resolve_mock = MagicMock(return_value = EmptyTestClass())
        self.server.album_instance.resolve = resolve_mock
        json = self.getJSONResponse(client, "/%s/catalog_local/group/name/version" % route)
        self.assertIsNotNone(json)
        self.server.task_manager().finish_tasks()
        self.assertEqual(1, route_mock.call_count)
        json = self.getJSONResponse(client, "/%s/group/name/version" % route)
        self.assertIsNotNone(json)
        self.server.task_manager().finish_tasks()
        self.assertEqual(2, route_mock.call_count)


if __name__ == '__main__':
    unittest.main()

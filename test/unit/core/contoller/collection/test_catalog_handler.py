import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock, call

from album.core.controller.collection.catalog_handler import CatalogHandler
from album.core.controller.collection.solution_handler import SolutionHandler
from album.core.model.catalog_updates import CatalogUpdates
from album.core.model.configuration import Configuration
from album.core.model.default_values import DefaultValues
from test.unit.core.contoller.collection.test_collection_manager import TestCatalogCollectionCommon


class TestCatalogHandler(TestCatalogCollectionCommon):

    def setUp(self):
        super().setUp()
        self.fill_catalog_collection()
        self.solution_handler = SolutionHandler(self.catalog_collection)
        self.catalogHandler = CatalogHandler(Configuration(), self.catalog_collection, self.solution_handler)

    def tearDown(self) -> None:
        super().tearDown()

    @unittest.skip("Needs to be implemented!")
    def test_create_local_catalog(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_add_initial_catalogs(self):
        # todo: implement
        pass

    def test_add_by_src(self):
        catalog_name = "aNiceCatalog"
        catalog_src = Path(self.tmp_dir.name).joinpath("my-catalogs", catalog_name)
        catalog_src.mkdir(parents=True)
        with open(catalog_src.joinpath(DefaultValues.catalog_index_metafile_json.value), 'w') as config:
            config.writelines("{\"name\": \"" + catalog_name + "\", \"version\": \"0.1.0\"}")

        # call
        self.catalogHandler.add_by_src(catalog_src)

        # assert
        expected_list = deepcopy(self.catalog_list)
        expected_list.append({
            "catalog_id": 4,
            "deletable": 1,
            "name": catalog_name,
            "path": str(Path(self.tmp_dir.name).joinpath("album", DefaultValues.catalog_folder_prefix.value, catalog_name)),
            "src": str(catalog_src),
        })
        self.assertEqual(expected_list, self.catalog_collection.get_all_catalogs())

    @unittest.skip("Needs to be implemented!")
    def test__add_to_index(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_by_id(self):
        # todo: implement
        pass

    def test_get_by_src(self):
        # call
        c = self.catalogHandler.get_by_src(str(DefaultValues.default_catalog_src.value))

        # assert
        self.assertEqual(c.name, "default")

    def test_get_by_name(self):
        expected_name = self.catalogHandler.get_all()[0].name

        # call & assert
        self.assertEqual(expected_name, self.catalogHandler.get_by_name(expected_name).name)

    def test_get_by_name_not_configured(self):
        with self.assertRaises(LookupError):
            self.catalogHandler.get_by_name("aFaultyId")

    def test_get_by_path(self):
        c = self.catalogHandler.get_by_path(self.catalog_list[0]['path'])
        self.assertEqual(c.name, self.catalog_list[0]['name'])

    def test_get_all(self):
        c = self.catalogHandler.get_all()

        self.assertEqual(len(c), 3)

        self.assertFalse(c[0].is_deletable)
        self.assertTrue(c[1].is_deletable)
        self.assertTrue(c[2].is_deletable)

    def test_get_local_catalog(self):
        r = self.catalogHandler.get_local_catalog()

        local_catalog = self.catalogHandler.get_all()[0]
        self.assertEqual(r.catalog_id, local_catalog.catalog_id)
        self.assertEqual(r.name, local_catalog.name)
        self.assertEqual(r.src, local_catalog.src)

    @unittest.skip("Needs to be implemented!")
    def test_create_new_catalog(self):
        # todo: implement
        pass

    def test__update(self):
        # mocks
        refresh_index = MagicMock(return_value=True)
        local_catalog = self.catalogHandler.get_local_catalog()
        local_catalog.refresh_index = refresh_index

        # call
        r = self.catalogHandler._update(local_catalog)

        # assert
        self.assertTrue(r)
        refresh_index.assert_called_once()

    def test_update_by_name(self):
        # mocks
        _update = MagicMock(return_value=True)
        self.catalogHandler._update = _update

        get_catalog_by_id = MagicMock(return_value="myCatalog")
        self.catalogHandler.get_by_name = get_catalog_by_id

        # call
        self.catalogHandler.update_by_name("aNiceName")

        # assert
        get_catalog_by_id.assert_called_once_with("aNiceName")
        _update.assert_called_once_with("myCatalog")

    def test_update_all(self):
        # mocks
        _update = MagicMock(return_value=True)
        self.catalogHandler._update = _update

        # call
        r = self.catalogHandler.update_all()

        self.assertEqual(3, _update.call_count)
        self.assertEqual([True, True, True], r)

    def test_update_all_failed(self):
        # mocks
        _update = MagicMock()
        _update.side_effect = [True, ConnectionError(), True]
        self.catalogHandler._update = _update

        # call
        r = self.catalogHandler.update_all()

        # assert
        self.assertEqual(3, _update.call_count)
        self.assertEqual([True, False, True], r)

    def test_update_any(self):
        # mocks
        update_all = MagicMock(return_value=None)
        self.catalogHandler.update_all = update_all
        update_by_name = MagicMock(return_value=None)
        self.catalogHandler.update_by_name = update_by_name

        # call
        self.catalogHandler.update_any("aNiceCatalogID")
        update_all.assert_not_called()
        update_by_name.assert_called_once()

    def test_update_any_no_id(self):
        # mocks
        update_all = MagicMock(return_value=None)
        self.catalogHandler.update_all = update_all

        update_by_name = MagicMock(return_value=None)
        self.catalogHandler.update_by_name = update_by_name

        # call
        self.catalogHandler.update_any()
        update_all.assert_called_once()
        update_by_name.assert_not_called()

    def test_update_collection(self):
        # mocks
        catalog = self.catalogHandler.get_local_catalog()
        _update_collection_from_catalog = MagicMock(return_value=CatalogUpdates(catalog))
        self.catalogHandler._update_collection_from_catalog = _update_collection_from_catalog

        # call
        res = self.catalogHandler.update_collection()

        # assert
        self.assertEqual(3, len(res))
        self.assertEqual(3, _update_collection_from_catalog.call_count)
        self.assertEqual(
            [call(catalog_name=catalog.name), call(catalog_name='default'), call(catalog_name='test_catalog2')],
            _update_collection_from_catalog.call_args_list)

    def test_update_collection_dry_run(self):
        # mocks
        catalog = self.catalogHandler.get_local_catalog()
        _get_divergence_between_catalog_and_collection = MagicMock(return_value=CatalogUpdates(catalog))
        _update_collection_from_catalog = MagicMock(return_value=None)
        self.catalogHandler._get_divergence_between_catalog_and_collection = \
            _get_divergence_between_catalog_and_collection
        self.catalogHandler._update_collection_from_catalog = _update_collection_from_catalog

        # call
        res = self.catalogHandler.update_collection(dry_run=True)

        # assert
        self.assertEqual(3, len(res))
        self.assertEqual(3, _get_divergence_between_catalog_and_collection.call_count)
        self.assertEqual(
            [call(catalog_name=catalog.name), call(catalog_name='default'), call(catalog_name='test_catalog2')],
            _get_divergence_between_catalog_and_collection.call_args_list)
        _update_collection_from_catalog.assert_not_called()

    def test_update_collection_specific_catalog(self):
        # mocks
        catalog = self.catalogHandler.get_local_catalog()
        _update_collection_from_catalog = MagicMock(return_value=CatalogUpdates(catalog))
        self.catalogHandler._update_collection_from_catalog = _update_collection_from_catalog

        # call
        res = self.catalogHandler.update_collection(catalog_name=catalog.name)

        # assert
        self.assertEqual(1, len(res))
        _update_collection_from_catalog.assert_called_once_with(catalog.name)

    def test_update_collection_specific_catalog_dry_run(self):
        # mocks
        catalog = self.catalogHandler.get_local_catalog()
        _get_divergence_between_catalog_and_collection = MagicMock(return_value=CatalogUpdates(catalog))
        _update_collection_from_catalog = MagicMock(return_value=CatalogUpdates(catalog))
        self.catalogHandler._get_divergence_between_catalog_and_collection = \
            _get_divergence_between_catalog_and_collection
        self.catalogHandler._update_collection_from_catalog = _update_collection_from_catalog

        # call
        res = self.catalogHandler.update_collection(catalog_name=catalog.name, dry_run=True)

        # assert
        self.assertEqual(1, len(res))
        _get_divergence_between_catalog_and_collection.assert_called_once_with(catalog.name)
        _update_collection_from_catalog.assert_not_called()

    @unittest.skip("Needs to be implemented!")
    def test__remove_from_collection(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_remove_from_collection_by_path(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_remove_from_collection_by_name(self):
        # todo: implement
        pass

    def test_remove_from_collection_by_name_undeletable(self):
        # call
        catalogs = self.catalog_collection.get_all_catalogs()
        x = self.catalogHandler.remove_from_collection_by_name(catalogs[0]['name'])

        # assert
        self.assertIsNone(x)
        self.assertEqual(self.catalog_list,
                         self.catalog_collection.get_all_catalogs())  # nothing changed

    def test_remove_from_collection_by_name_invalid_name(self):
        # call
        x = self.catalogHandler.remove_from_collection_by_name("aWrongIdOfACatalogToRemove")

        # assert
        self.assertIsNone(x)
        self.assertEqual(self.catalog_list,
                         self.catalog_collection.get_all_catalogs())  # nothing changed

    @unittest.skip("Needs to be implemented!")
    def test_remove_from_collection_by_src(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_all_as_dict(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__create_catalog_from_src(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__create_catalog_cache_if_missing(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__get_divergence_between_catalogs_and_collection(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__get_divergence_between_catalog_and_collection(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__update_collection_from_catalogs(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__update_collection_from_catalog(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__compare_solutions(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__as_catalog(self):
        # todo: implement
        pass

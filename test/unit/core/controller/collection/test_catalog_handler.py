from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from album.core.controller.collection.catalog_handler import CatalogHandler
from album.core.controller.collection.solution_handler import SolutionHandler
from album.core.controller.migration_manager import MigrationManager
from album.core.model.catalog import Catalog
from album.core.model.catalog_index import CatalogIndex
from album.core.model.catalog_updates import CatalogUpdates, SolutionChange, ChangeType
from album.core.model.configuration import Configuration
from album.core.model.coordinates import Coordinates
from album.core.model.default_values import DefaultValues
from test.unit.core.controller.collection.test_collection_manager import TestCatalogCollectionCommon


class TestCatalogHandler(TestCatalogCollectionCommon):

    def setUp(self):
        super().setUp()
        self.fill_catalog_collection()
        self.solution_handler = SolutionHandler(self.catalog_collection)
        self.catalog_handler = CatalogHandler(Configuration(), self.catalog_collection, self.solution_handler)


    def test_create_local_catalog(self):
        # mocks
        create_new_catalog_mock = MagicMock()
        self.catalog_handler.create_new_catalog = create_new_catalog_mock

        # call
        self.catalog_handler.create_local_catalog()

        # assert
        create_new_catalog_mock.assert_called_once_with(
            Configuration().get_cache_path_catalog("catalog_local"), "catalog_local"
        )

    def test_add_initial_catalogs(self):
        # mocks
        add_by_src_mock = MagicMock()
        self.catalog_handler.add_by_src = add_by_src_mock

        # call
        self.catalog_handler.add_initial_catalogs()

        # assert
        self.assertEqual(2, add_by_src_mock.call_count)

    def test_add_by_src(self):
        catalog_name = "aNiceCatalog"
        catalog_src = Path(self.tmp_dir.name).joinpath("my-catalogs", catalog_name)
        catalog_src.mkdir(parents=True)
        with open(catalog_src.joinpath(DefaultValues.catalog_index_metafile_json.value), 'w') as config:
            config.writelines("{\"name\": \"" + catalog_name + "\", \"version\": \"0.1.0\"}")

        # call
        catalog = self.catalog_handler.add_by_src(catalog_src)

        # assert
        expected_list = deepcopy(self.catalog_list)
        expected_list.append({
            "catalog_id": 4,
            "deletable": 1,
            "name": catalog_name,
            "path": str(
                Path(self.tmp_dir.name).joinpath("album", DefaultValues.catalog_folder_prefix.value, catalog_name)),
            "src": str(catalog_src),
        })
        self.assertEqual(expected_list, self.catalog_collection.get_all_catalogs())

    def test__add_to_index(self):
        # prepare
        catalog_path = Path(self.tmp_dir.name).joinpath("myDir")
        catalog_to_add = Catalog(None, "mycatalog", catalog_path)

        # mocks
        insert_catalog_mock = MagicMock(return_value=1)
        self.catalog_handler.catalog_collection.insert_catalog = insert_catalog_mock

        # call
        self.catalog_handler._add_to_index(catalog_to_add)

        # assert
        insert_catalog_mock.assert_called_once_with("mycatalog", 'None', str(catalog_path), 1)

    def test_get_by_id(self):
        # mocks
        get_catalog_mock = MagicMock(return_value="mycatalog")
        self.catalog_handler.catalog_collection.get_catalog = get_catalog_mock

        _as_catalog_mock = MagicMock()
        self.catalog_handler._as_catalog = _as_catalog_mock

        # call
        self.catalog_handler.get_by_id(50)

        # assert
        get_catalog_mock.assert_called_once_with(50)
        _as_catalog_mock.assert_called_once_with("mycatalog")

    def test_get_by_id_not_found(self):
        # mocks
        get_catalog_mock = MagicMock(return_value=None)
        self.catalog_handler.catalog_collection.get_catalog = get_catalog_mock

        _as_catalog_mock = MagicMock()
        self.catalog_handler._as_catalog = _as_catalog_mock

        # call
        with self.assertRaises(LookupError):
            self.catalog_handler.get_by_id(50)

        # assert
        get_catalog_mock.assert_called_once_with(50)
        _as_catalog_mock.assert_not_called()

    def test_get_by_src(self):
        # call
        c = self.catalog_handler.get_by_src(str(DefaultValues.default_catalog_src.value))

        # assert
        self.assertEqual(c.name, "default")

    def test_get_by_name(self):
        expected_name = self.catalog_handler.get_all()[0].name

        # call & assert
        self.assertEqual(expected_name, self.catalog_handler.get_by_name(expected_name).name)

    def test_get_by_name_not_configured(self):
        with self.assertRaises(LookupError):
            self.catalog_handler.get_by_name("aFaultyId")

    def test_get_by_path(self):
        c = self.catalog_handler.get_by_path(self.catalog_list[0]['path'])
        self.assertEqual(c.name, self.catalog_list[0]['name'])

    def test_get_all(self):
        c = self.catalog_handler.get_all()

        self.assertEqual(len(c), 3)

        self.assertFalse(c[0].is_deletable)
        self.assertTrue(c[1].is_deletable)
        self.assertTrue(c[2].is_deletable)

    def test_get_local_catalog(self):
        r = self.catalog_handler.get_local_catalog()

        local_catalog = self.catalog_handler.get_all()[0]
        self.assertEqual(r.catalog_id, local_catalog.catalog_id)
        self.assertEqual(r.name, local_catalog.name)
        self.assertEqual(r.src, local_catalog.src)

    def test_create_new_catalog(self):
        # prepare
        local_path = Path(self.tmp_dir.name).joinpath("myNewCatalogPath")
        name = "myNewCatalogName"

        # call
        self.catalog_handler.create_new_catalog(local_path, name)

        # assert
        self.assertTrue(local_path.exists())
        self.assertTrue(local_path.joinpath("album_catalog_index.json").exists())
        with open(local_path.joinpath("album_catalog_index.json"), "r") as f:
            metafile = f.readlines()
            self.assertEqual("{\"name\": \"myNewCatalogName\", \"version\": \"0.1.0\"}", metafile[0])

    def test__update(self):
        # mocks
        refresh_index = MagicMock(return_value=True)
        local_catalog = self.catalog_handler.get_local_catalog()
        MigrationManager().refresh_index = refresh_index

        # call
        r = self.catalog_handler._update(local_catalog)

        # assert
        self.assertTrue(r)
        refresh_index.assert_called_once()

    def test_update_by_name(self):
        # mocks
        _update = MagicMock(return_value=True)
        self.catalog_handler._update = _update

        get_catalog_by_id = MagicMock(return_value="myCatalog")
        self.catalog_handler.get_by_name = get_catalog_by_id

        # call
        self.catalog_handler.update_by_name("aNiceName")

        # assert
        get_catalog_by_id.assert_called_once_with("aNiceName")
        _update.assert_called_once_with("myCatalog")

    def test_update_all(self):
        # mocks
        _update = MagicMock(return_value=True)
        self.catalog_handler._update = _update

        # call
        r = self.catalog_handler.update_all()

        self.assertEqual(3, _update.call_count)
        self.assertEqual([True, True, True], r)

    def test_update_all_failed(self):
        # mocks
        _update = MagicMock()
        _update.side_effect = [True, ConnectionError(), True]
        self.catalog_handler._update = _update

        # call
        r = self.catalog_handler.update_all()

        # assert
        self.assertEqual(3, _update.call_count)
        self.assertEqual([True, False, True], r)

    def test_update_any(self):
        # mocks
        update_all = MagicMock(return_value=None)
        self.catalog_handler.update_all = update_all
        update_by_name = MagicMock(return_value=None)
        self.catalog_handler.update_by_name = update_by_name

        # call
        self.catalog_handler.update_any("aNiceCatalogID")
        update_all.assert_not_called()
        update_by_name.assert_called_once()

    def test_update_any_no_id(self):
        # mocks
        update_all = MagicMock(return_value=None)
        self.catalog_handler.update_all = update_all

        update_by_name = MagicMock(return_value=None)
        self.catalog_handler.update_by_name = update_by_name

        # call
        self.catalog_handler.update_any()
        update_all.assert_called_once()
        update_by_name.assert_not_called()

    def test_update_collection(self):
        # mocks
        catalog = self.catalog_handler.get_local_catalog()
        _update_collection_from_catalog = MagicMock(return_value=CatalogUpdates(catalog))
        self.catalog_handler._update_collection_from_catalog = _update_collection_from_catalog

        # call
        res = self.catalog_handler.update_collection()

        # assert
        self.assertEqual(3, len(res))
        self.assertEqual(3, _update_collection_from_catalog.call_count)
        self.assertEqual(
            [call(catalog_name=catalog.name), call(catalog_name='default'), call(catalog_name='test_catalog2')],
            _update_collection_from_catalog.call_args_list)

    def test_update_collection_dry_run(self):
        # mocks
        catalog = self.catalog_handler.get_local_catalog()
        _get_divergence_between_catalog_and_collection = MagicMock(return_value=CatalogUpdates(catalog))
        _update_collection_from_catalog = MagicMock(return_value=None)
        self.catalog_handler._get_divergence_between_catalog_and_collection = \
            _get_divergence_between_catalog_and_collection
        self.catalog_handler._update_collection_from_catalog = _update_collection_from_catalog

        # call
        res = self.catalog_handler.update_collection(dry_run=True)

        # assert
        self.assertEqual(3, len(res))
        self.assertEqual(3, _get_divergence_between_catalog_and_collection.call_count)
        self.assertEqual(
            [call(catalog_name=catalog.name), call(catalog_name='default'), call(catalog_name='test_catalog2')],
            _get_divergence_between_catalog_and_collection.call_args_list)
        _update_collection_from_catalog.assert_not_called()

    def test_update_collection_specific_catalog(self):
        # mocks
        catalog = self.catalog_handler.get_local_catalog()
        _update_collection_from_catalog = MagicMock(return_value=CatalogUpdates(catalog))
        self.catalog_handler._update_collection_from_catalog = _update_collection_from_catalog

        # call
        res = self.catalog_handler.update_collection(catalog_name=catalog.name)

        # assert
        self.assertEqual(1, len(res))
        _update_collection_from_catalog.assert_called_once_with(catalog.name)

    def test_update_collection_specific_catalog_dry_run(self):
        # mocks
        catalog = self.catalog_handler.get_local_catalog()
        _get_divergence_between_catalog_and_collection = MagicMock(return_value=CatalogUpdates(catalog))
        _update_collection_from_catalog = MagicMock(return_value=CatalogUpdates(catalog))
        self.catalog_handler._get_divergence_between_catalog_and_collection = \
            _get_divergence_between_catalog_and_collection
        self.catalog_handler._update_collection_from_catalog = _update_collection_from_catalog

        # call
        res = self.catalog_handler.update_collection(catalog_name=catalog.name, dry_run=True)

        # assert
        self.assertEqual(1, len(res))
        _get_divergence_between_catalog_and_collection.assert_called_once_with(catalog.name)
        _update_collection_from_catalog.assert_not_called()

    @patch('album.core.controller.collection.catalog_handler.force_remove')
    def test__remove_from_collection(self, force_remove_mock):
        # prepare
        catalog_dict = {
            'catalog_id': 1,
            'name': "myCatalog",
            'path': "myPath",
            'src': "mySrc",
            'deletable': True
        }
        catalog = self.catalog_handler._as_catalog(catalog_dict)

        # mocks
        get_by_id_mock = MagicMock(return_value=catalog)
        self.catalog_handler.get_by_id = get_by_id_mock

        remove_catalog_mock = MagicMock()
        self.catalog_handler.catalog_collection.remove_catalog = remove_catalog_mock

        # call
        c = self.catalog_handler._remove_from_collection(catalog_dict)

        # assert
        get_by_id_mock.assert_called_once_with(1)
        force_remove_mock.assert_called_once_with(Path("myPath"))
        self.assertEqual(catalog, c)

    @patch('album.core.controller.collection.catalog_handler.force_remove')
    def test__remove_from_collection_not_configured(self, force_remove_mock):
        # prepare
        catalog_dict = {
            'catalog_id': 1,
            'name': "myCatalog",
            'path': "myPath",
            'src': "mySrc",
            'deletable': True
        }

        # mocks
        get_by_id_mock = MagicMock(side_effect=LookupError(""))
        self.catalog_handler.get_by_id = get_by_id_mock

        remove_catalog_mock = MagicMock()
        self.catalog_handler.catalog_collection.remove_catalog = remove_catalog_mock

        # call
        with self.assertRaises(LookupError):
            self.catalog_handler._remove_from_collection(catalog_dict)

        # assert
        get_by_id_mock.assert_called_once_with(1)
        force_remove_mock.assert_not_called()

    @patch('album.core.controller.collection.catalog_handler.force_remove')
    def test__remove_from_collection_not_deletable(self, force_remove_mock):
        # prepare
        catalog_dict = {
            'catalog_id': 1,
            'name': "myCatalog",
            'path': "myPath",
            'src': "mySrc",
            'deletable': False
        }
        catalog = self.catalog_handler._as_catalog(catalog_dict)

        # mocks
        get_by_id_mock = MagicMock(return_value=catalog)
        self.catalog_handler.get_by_id = get_by_id_mock

        remove_catalog_mock = MagicMock()
        self.catalog_handler.catalog_collection.remove_catalog = remove_catalog_mock

        # call
        c = self.catalog_handler._remove_from_collection(catalog_dict)

        # assert
        self.assertIsNone(c)
        get_by_id_mock.assert_called_once_with(1)
        force_remove_mock.assert_not_called()

    def test_remove_from_collection_by_path(self):
        # mock
        get_catalog_by_path_mock = MagicMock(return_value={"a": 1})
        self.catalog_handler.catalog_collection.get_catalog_by_path = get_catalog_by_path_mock

        _remove_from_collection_mock = MagicMock(return_value="myCatalogObject")
        self.catalog_handler._remove_from_collection = _remove_from_collection_mock

        # call
        c = self.catalog_handler.remove_from_collection_by_path("mypath")

        # assert
        get_catalog_by_path_mock.assert_called_once_with("mypath")
        _remove_from_collection_mock.assert_called_once_with({"a": 1})
        self.assertEqual("myCatalogObject", c)

    def test_remove_from_collection_by_path_no_catalog(self):
        # mock
        get_catalog_by_path_mock = MagicMock(return_value=None)
        self.catalog_handler.catalog_collection.get_catalog_by_path = get_catalog_by_path_mock

        _remove_from_collection_mock = MagicMock(return_value="myCatalogObject")
        self.catalog_handler._remove_from_collection = _remove_from_collection_mock

        # call
        c = self.catalog_handler.remove_from_collection_by_path("mypath")

        # assert
        get_catalog_by_path_mock.assert_called_once_with("mypath")
        _remove_from_collection_mock.assert_not_called()
        self.assertIsNone(c)

    def test_remove_from_collection_by_name(self):
        # mock
        get_catalog_by_name_mock = MagicMock(return_value={"a": 1})
        self.catalog_handler.catalog_collection.get_catalog_by_name = get_catalog_by_name_mock

        _remove_from_collection_mock = MagicMock(return_value="myCatalogObject")
        self.catalog_handler._remove_from_collection = _remove_from_collection_mock

        # call
        c = self.catalog_handler.remove_from_collection_by_name("myname")

        # assert
        get_catalog_by_name_mock.assert_called_once_with("myname")
        _remove_from_collection_mock.assert_called_once_with({"a": 1})
        self.assertEqual("myCatalogObject", c)

    def test_remove_from_collection_by_name_no_catalog(self):
        # mock
        get_catalog_by_name_mock = MagicMock(return_value=None)
        self.catalog_handler.catalog_collection.get_catalog_by_name = get_catalog_by_name_mock

        _remove_from_collection_mock = MagicMock(return_value="myCatalogObject")
        self.catalog_handler._remove_from_collection = _remove_from_collection_mock

        # call
        c = self.catalog_handler.remove_from_collection_by_name("myname")

        # assert
        get_catalog_by_name_mock.assert_called_once_with("myname")
        _remove_from_collection_mock.assert_not_called()
        self.assertIsNone(c)

    def test_remove_from_collection_by_name_undeletable(self):
        # call
        catalogs = self.catalog_collection.get_all_catalogs()
        x = self.catalog_handler.remove_from_collection_by_name(catalogs[0]['name'])

        # assert
        self.assertIsNone(x)
        self.assertEqual(self.catalog_list,
                         self.catalog_collection.get_all_catalogs())  # nothing changed

    def test_remove_from_collection_by_name_invalid_name(self):
        # call
        x = self.catalog_handler.remove_from_collection_by_name("aWrongIdOfACatalogToRemove")

        # assert
        self.assertIsNone(x)
        self.assertEqual(self.catalog_list,
                         self.catalog_collection.get_all_catalogs())  # nothing changed

    def test_remove_from_collection_by_src(self):
        # mock
        get_catalog_by_src_mock = MagicMock(return_value={"a": 1})
        self.catalog_handler.catalog_collection.get_catalog_by_src = get_catalog_by_src_mock

        _remove_from_collection_mock = MagicMock(return_value="myCatalogObject")
        self.catalog_handler._remove_from_collection = _remove_from_collection_mock

        # call
        c = self.catalog_handler.remove_from_collection_by_src(self.tmp_dir.name)

        # assert
        get_catalog_by_src_mock.assert_called_once_with(self.tmp_dir.name)
        _remove_from_collection_mock.assert_called_once_with({"a": 1})
        self.assertEqual("myCatalogObject", c)

    def test_remove_from_collection_by_src_no_catalog(self):
        # mock
        get_catalog_by_src_mock = MagicMock(return_value=None)
        self.catalog_handler.catalog_collection.get_catalog_by_src = get_catalog_by_src_mock

        _remove_from_collection_mock = MagicMock(return_value="myCatalogObject")
        self.catalog_handler._remove_from_collection = _remove_from_collection_mock

        # call
        c = self.catalog_handler.remove_from_collection_by_src(self.tmp_dir.name)

        # assert
        get_catalog_by_src_mock.assert_called_once_with(self.tmp_dir.name)
        _remove_from_collection_mock.assert_not_called()
        self.assertIsNone(c)

    def test_get_all_as_dict(self):
        # mocks
        get_all_catalogs_mock = MagicMock(return_value="abc")
        self.catalog_handler.catalog_collection.get_all_catalogs = get_all_catalogs_mock

        # call
        x = self.catalog_handler.get_all_as_dict()

        # assert
        self.assertEqual({"catalogs": "abc"}, x)

    def test__create_catalog_from_src(self):
        with patch("album.core.model.catalog.Catalog.retrieve_catalog_meta_information") as retrieve_c_m_i_mock:
            retrieve_c_m_i_mock.side_effect = [{"name": "mynewcatalog", "version": "0.1.0"}]

            # call
            catalog = self.catalog_handler._create_catalog_from_src(self.tmp_dir.name)

            # assert
            self.assertEqual("mynewcatalog", catalog.name)
            self.assertEqual(Path(self.tmp_dir.name), catalog.src)
            self.assertEqual(Configuration().get_cache_path_catalog("mynewcatalog"), catalog.path)
            self.assertIsNone(catalog.catalog_id)

    def test__create_catalog_cache_if_missing(self):
        # prepare
        p = Path(self.tmp_dir.name).joinpath("n")
        c = Catalog(None, "n", p)

        # pre-assert
        self.assertFalse(p.exists())

        # call
        self.catalog_handler._create_catalog_cache_if_missing(c)

        # assert
        self.assertTrue(p.exists())

    def test__get_divergence_between_catalogs_and_collection(self):
        # mock
        _get_divergence_b_catalog_a_coll_mock = MagicMock(return_value=1)
        self.catalog_handler._get_divergence_between_catalog_and_collection = _get_divergence_b_catalog_a_coll_mock

        get_all_mock = MagicMock(return_value=[Catalog(None, "n", "p"), Catalog(None, "m", "r")])
        self.catalog_handler.get_all = get_all_mock

        # call
        x = self.catalog_handler._get_divergence_between_catalogs_and_collection()

        # assert
        self.assertEqual(2, _get_divergence_b_catalog_a_coll_mock.call_count)
        self.assertEqual([1, 1], x)

    def test__get_divergence_between_catalog_and_collection(self):
        # prepare
        Path(self.tmp_dir.name).joinpath("myCatalogSrc").touch()
        c1 = Catalog(None, "n", self.tmp_dir.name, src=Path(self.tmp_dir.name).joinpath("myCatalogSrc"))
        c1_index = CatalogIndex("n", Path(self.tmp_dir.name).joinpath("album_catalog_index.db"))

        # mock
        get_by_name_mock = MagicMock(return_value=c1)
        self.catalog_handler.get_by_name = get_by_name_mock

        get_solutions_by_catalog_mock = MagicMock(return_value=[])
        self.catalog_handler.catalog_collection.get_solutions_by_catalog = get_solutions_by_catalog_mock

        _compare_solutions_mock = MagicMock(return_value=None)
        self.catalog_handler._compare_solutions = _compare_solutions_mock

        r_val = [
            {"group": "g1", "name": "n1", "version": "v1"},
            {"group": "g1", "name": "n2", "version": "v1"}
        ]
        get_all_solutions_mock = MagicMock(return_value=r_val)
        c1_index.get_all_solutions = get_all_solutions_mock
        c1.catalog_index = c1_index

        with patch("album.core.controller.migration_manager.MigrationManager.load_index") as load_index_mock:
            load_index_mock.return_value = c1

            # call
            self.catalog_handler._get_divergence_between_catalog_and_collection("n")

            # assert
            get_by_name_mock.assert_called_once_with("n")
            get_solutions_by_catalog_mock.assert_called_once_with(None)
            load_index_mock.assert_called_once_with(c1)
            get_all_solutions_mock.assert_called_once()
            _compare_solutions_mock.assert_called_once_with([], r_val)

    def test__update_collection_from_catalogs(self):
        # prepare
        c1 = Catalog(None, "n", "p")
        c2 = Catalog(None, "m", "r")
        s_e = [CatalogUpdates(c1), CatalogUpdates(c2)]

        # mock
        _update_collection_from_catalog_mock = MagicMock(side_effect=s_e)
        self.catalog_handler._update_collection_from_catalog = _update_collection_from_catalog_mock

        get_all_mock = MagicMock(return_value=[c1, c2])
        self.catalog_handler.get_all = get_all_mock

        # call
        x = self.catalog_handler._update_collection_from_catalogs()

        # assert
        self.assertEqual(2, _update_collection_from_catalog_mock.call_count)
        self.assertEqual(s_e, x)

    def test__update_collection_from_catalog(self):
        # prepare
        c1 = Catalog(None, "n", "p")

        c_updates = CatalogUpdates(c1)

        sol_change_list = [
            SolutionChange(Coordinates("g", "n1", "v"), ChangeType.ADDED),
            SolutionChange(Coordinates("g", "n2", "v"), ChangeType.CHANGED)
        ]

        c_updates.solution_changes = sol_change_list

        # mock
        _get_div_b_cat_and_coll_mock = MagicMock(return_value=c_updates)
        self.catalog_handler._get_divergence_between_catalog_and_collection = _get_div_b_cat_and_coll_mock

        apply_change_mock = MagicMock()
        self.solution_handler.apply_change = apply_change_mock

        # call
        u = self.catalog_handler._update_collection_from_catalog("n")

        # assert
        self.assertEqual(2, apply_change_mock.call_count)
        _get_div_b_cat_and_coll_mock.assert_called_once_with("n")
        self.assertEqual(c_updates, u)

    def test__compare_solutions(self):
        # prepare
        solutions_old = [
            {"hash": 1, "group": "g1", "name": "n1", "version": "v1"},
            {"hash": 2, "group": "g2", "name": "n2", "version": "v1"},  # deleted
            {"hash": 3, "group": "g3", "name": "n3", "version": "v1"}
        ]
        solutions_new = [
            {"hash": 1, "group": "g1", "name": "n1", "version": "v1"},  # not touched
            {"hash": 9, "group": "g3", "name": "n3", "version": "v1"},  # changed in some other attributes (not shown)
            {"hash": 4, "group": "g4", "name": "n4", "version": "v1"}  # new
        ]

        r = CatalogHandler._compare_solutions(solutions_old, solutions_new)

        expected_result = [
            SolutionChange(Coordinates("g3", "n3", "v1"), ChangeType.CHANGED),
            SolutionChange(Coordinates("g2", "n2", "v1"), ChangeType.REMOVED),
            SolutionChange(Coordinates("g4", "n4", "v1"), ChangeType.ADDED)
        ]

        self.assertCountEqual(expected_result, r)

    def test__as_catalog(self):
        catalog_dict = {
            'catalog_id': 1,
            'name': "myCatalog",
            'path': "myPath",
            'src': "mySrc",
            'deletable': True
        }

        c = self.catalog_handler._as_catalog(catalog_dict)

        self.assertEqual("myCatalog", c.name)
        self.assertEqual(Path("myPath"), c.path)
        self.assertEqual("mySrc", c.src)
        self.assertEqual(1, c.catalog_id)
        self.assertEqual(1, c.is_deletable)
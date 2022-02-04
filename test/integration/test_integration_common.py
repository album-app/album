from pathlib import Path
from unittest.mock import patch, MagicMock

from album.api import Album
from album.core.controller.album_controller import AlbumController
from album.core.model.default_values import DefaultValues
from test.integration.test_integration_core_common import TestIntegrationCoreCommon
from test.global_exception_watcher import GlobalExceptionWatcher


class TestIntegrationCommon(TestIntegrationCoreCommon):

    def setUp(self):

        self._create_tmp_resources()

        self.album_instance = Album.Builder().base_cache_path(self.tmp_dir.name).build()

        self.configure_silent_test_logging('album')

        self.create_album_instance_patch = patch('album.argument_parsing.create_album_instance',
                                                 return_value=self.album_instance)
        self.create_album_instance_patch.start()

        self.collection_initialized = False

    def tearDown(self) -> None:
        self.create_album_instance_patch.stop()
        if self.collection_initialized:
            self._remove_test_environments()
        self.album_instance.close()
        self._cleanup_logging_tmp()

    def init_collection(self, init_catalogs=True):
        self.collection_initialized = True

        if init_catalogs:
            catalogs_dict = {
                DefaultValues.local_catalog_name.value:
                    Path(self.tmp_dir.name).joinpath("album", DefaultValues.catalog_folder_prefix.value,
                                                     DefaultValues.local_catalog_name.value)
            }
            get_initial_catalogs_mock = MagicMock(
                return_value=catalogs_dict
            )
            self.album_instance.configuration().get_initial_catalogs = get_initial_catalogs_mock
            # create collection
            self.collection_manager().load_or_create()
        else:
            # mock retrieve_catalog_meta_information as it involves a http request
            with patch("album.core.controller.collection.catalog_handler.CatalogHandler.add_initial_catalogs"):
                self.collection_manager().load_or_create()

    def collection_manager(self):
        return self.album_instance._controller.collection_manager()

    def album_controller(self) -> AlbumController:
        return self.album_instance._controller

    def album(self) -> Album:
        return self.album_instance

    def run(self, result=None):
        # add watcher to catch any exceptions thrown in threads
        with GlobalExceptionWatcher():
            super(TestIntegrationCommon, self).run(result)

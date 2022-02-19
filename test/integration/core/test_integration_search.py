import unittest

from test.integration.test_integration_core_common import TestIntegrationCoreCommon


class TestIntegrationSearch(TestIntegrationCoreCommon):

    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    def test_search_emtpy_index(self):
        self.album_controller.search_manager().search("keyword")
        self.assertNotIn('ERROR', self.captured_output.getvalue())


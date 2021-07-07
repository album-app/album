import unittest

from hips.core.controller.resolve_manager import ResolveManager
from test.unit.test_common import TestHipsCommon


class TestResolveManager(TestHipsCommon):
    def setUp(self):
        self.create_test_config()
        self.create_test_hips_no_env()

        self.resolve_manager = ResolveManager()

    def tearDown(self) -> None:
        super().tearDown()
        ResolveManager.instance = None

    @unittest.skip("Needs to be implemented!")
    def test_resolve_and_load(self):
        # ToDo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_resolve_dependency_and_load(self):
        # ToDo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__resolve_outside_catalog(self):
        # ToDo: implement
        pass

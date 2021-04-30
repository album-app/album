import unittest.mock
from argparse import Namespace
from unittest.mock import Mock
from unittest.mock import patch

import hips.core as hips
from hips.core import setup
from hips.core.install import install
from test.unit.test_common import TestHipsCommon


class TestHipsInstall(TestHipsCommon):

    def setUp(self):
        pass

    def __install_hips(self, _):
        setup(**vars(self.attrs))
        return hips.get_active_hips()

    @patch('hips.core.install.__add_to_local_catalog', return_value=True)
    @patch('hips.core.install.load_and_push_hips')
    @patch('hips.core.install.run_in_environment')
    @patch('hips.core.install.create_script')
    @patch('hips.core.search.HipsCatalogConfiguration.resolve_from_str')
    def test_install(self, resolve_mock, _, run_in_environment_mock, load_mock, __):
        # setup mocks
        load_mock.side_effect = self.__install_hips
        resolve_mock.side_effect = [{"path": "", "catalog": ""}]

        # setup fake hips
        self.attrs = Namespace(
            path="",
            name="",
            min_hips_version="",
            dependencies={'environment_name': 'hips'},
            install=Mock()
        )

        # test install call
        self.assertIsNone(install(self.attrs))
        self.assertEqual(1, load_mock.call_count)
        self.assertEqual(1, run_in_environment_mock.call_count)


if __name__ == '__main__':
    unittest.main()

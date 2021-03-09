import unittest.mock
from argparse import Namespace
from unittest.mock import Mock
from unittest.mock import patch

from hips import setup
from hips.install import install
from test.unit.test_common import TestHipsCommon


class TestHipsInstall(TestHipsCommon):

    def setUp(self):
        pass

    def __install_hips(self, _):
        setup(**self.attrs)
        pass

    @patch('hips.load_and_push_hips')
    def test_install(self, load_mock):
        # setup mocks
        install_mock = Mock()
        load_mock.side_effect = self.__install_hips

        # setup fake hips
        self.attrs = {
            "path": "",
            "name": "",
            "install": install_mock
        }
        self.args = Namespace(**self.attrs)

        # test install call
        self.assertIsNone(install(self.args))
        self.assertEqual(1, load_mock.call_count)
        self.assertEqual(1, install_mock.call_count)


if __name__ == '__main__':
    unittest.main()

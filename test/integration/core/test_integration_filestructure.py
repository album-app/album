import platform
from os import listdir
from pathlib import Path
from unittest.mock import patch

from album.core.model.environment import Environment
from album.core.utils.operations.file_operations import get_link_target
from test.integration.test_integration_core_common import TestIntegrationCoreCommon


class TestIntegrationFileStructure(TestIntegrationCoreCommon):
    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    @patch('album.core.controller.environment_manager.EnvironmentManager.install_environment')
    @patch('album.core.controller.environment_manager.EnvironmentManager.remove_environment')
    @patch('album.core.controller.install_manager.EnvironmentManager.remove_disc_content_from_environment')
    def test_file_structure(self, _, __, install_environment, get_environment_path):
        get_environment_path.return_value = self.album_controller.environment_manager().get_conda_manager().get_active_environment_path()
        environment = Environment({},
                                  self.album_controller.environment_manager().get_conda_manager().get_active_environment_name(),
                                  None)
        environment.set_path(self.album_controller.environment_manager().get_conda_manager().get_active_environment_path())
        install_environment.return_value = environment

        base = Path(self.album_controller.configuration().base_cache_path())
        self.assertFalse(base.joinpath('lnk').exists())

        # install and uninstall working solution
        solution = self.get_test_solution_path('solution11_minimal.py')
        self.album_controller.install_manager().install(solution)
        self.check_files_exist(base, 'group', 'name', '0.1.0', size=1)
        self.album_controller.install_manager().uninstall(solution)
        self.check_files_do_not_exist(base, 'group', 'name', '0.1.0', size=0)

        # install a solution that fails during install
        solution = self.get_test_solution_path('solution13_faulty_routine.py')
        with self.assertRaises(RuntimeError):
            self.album_controller.install_manager().install(solution)
        self.check_files_exist(base, 'group', 'faultySolution', '0.1.0', size=1)

        # install the working solution again (other coordinates)
        solution = self.get_test_solution_path('solution11_minimal.py')
        self.album_controller.install_manager().install(solution)
        self.check_files_exist(base, 'group', 'name', '0.1.0', size=1, id='0')

        # install a solution that fails during install
        solution = self.get_test_solution_path('solution13_faulty_routine.py')
        with self.assertRaises(RuntimeError):
            self.album_controller.install_manager().install(solution)
        self.check_files_exist(base, 'group', 'faultySolution', '0.1.0', size=2, id='1')

        # install a fixed version with the same coordinates
        solution = self.get_test_solution_path('solution13_faulty_routine_fixed.py')
        self.album_controller.install_manager().install(solution)
        self.check_files_exist(base, 'group', 'faultySolution', '0.1.0', size=2, id='1')

    def check_files_exist(self, base, group, name, version, size, id='0'):
        self.assertEqual(size, len(listdir(base.joinpath('lnk', 'pck'))))
        self.assertEqual(size, len(listdir(base.joinpath('lnk', 'inst'))))
        self.assertTrue(base.joinpath('lnk', 'pck', id).exists())
        self.assertTrue(base.joinpath('lnk', 'inst', id).exists())

        self.assertTrue(self._link(base.joinpath('catalogs', 'cache_catalog', 'solutions', group, name, version)).exists())
        self.assertEqual(base.joinpath('lnk', 'pck', id).resolve(), get_link_target(
            base.joinpath('catalogs', 'cache_catalog', 'solutions', group, name, version)).resolve())

        self.assertTrue(self._link(base.joinpath('installations', 'cache_catalog', group, name, version)).exists())
        self.assertEqual(base.joinpath('lnk', 'inst', id).resolve(), get_link_target(
            base.joinpath('installations', 'cache_catalog', group, name, version)).resolve())

    def check_files_do_not_exist(self, base, group, name, version, size, id='0'):
        self.assertEqual(size, len(listdir(base.joinpath('lnk', 'pck'))))
        self.assertEqual(size, len(listdir(base.joinpath('lnk', 'inst'))))
        self.assertFalse(base.joinpath('lnk', 'pck', id).exists())
        self.assertFalse(base.joinpath('lnk', 'inst', id).exists())
        self.assertFalse(self._link(base.joinpath('catalogs', 'cache_catalog', 'solutions', group, name, version)).exists())
        self.assertFalse(self._link(base.joinpath('installations', 'cache_catalog', group, name, version)).exists())

    def _link(self, link: Path):
        operation_system = platform.system().lower()
        if 'windows' in operation_system:
            return Path(str(link) + '.lnk')
        else:
            return link

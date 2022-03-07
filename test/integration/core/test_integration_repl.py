import os
import subprocess
import sys

import pexpect

from test.integration.test_integration_core_common import TestIntegrationCoreCommon


class TestIntegrationRepl(TestIntegrationCoreCommon):

    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    def test_repl(self):
        solution_path = self.get_test_solution_path('solution8_arguments.py')
        self.fake_install(solution_path)
        env = os.environ.copy()
        env['ALBUM_BASE_CACHE_PATH'] = str(self.album_controller.configuration().base_cache_path())
        if hasattr(pexpect, 'spawn'):
            cmd = ['-m', 'album', 'repl', solution_path]
            child = pexpect.spawn(sys.executable, cmd, env=env)
            child.sendline('import album')
            self.assertEqual(0, child.expect(r'>>>'))
            child.sendline('from album.runner.api import get_environment_name')
            self.assertEqual(0, child.expect(r'>>>'))
            child.sendline('print(get_environment_name())')
            self.assertEqual(0, child.expect(r'cache_catalog_group_solution8_arguments_0.1.0'))
            child.sendline('exit()')
            child.close()
        else:
            cmd = ['album', 'repl', solution_path]
            p = subprocess.Popen(cmd, env=env, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p.communicate(b"exit()\r")
            self.assertEqual(0, p.returncode)



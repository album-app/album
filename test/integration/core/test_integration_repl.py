import os
import subprocess
import sys
import unittest

import pexpect

from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationRepl(TestIntegrationCommon):

    def test_repl(self):
        self.fake_install(self.get_test_solution_path())
        env = os.environ.copy()
        env['ALBUM_BASE_CACHE_PATH'] = str(self.album_instance.configuration().base_cache_path())
        if hasattr(pexpect, 'spawn'):
            cmd = ['-m', 'album', 'repl', self.get_test_solution_path()]
            child = pexpect.spawn(sys.executable, cmd, env=env)
            child.sendline('import album')
            self.assertEqual(0, child.expect(r'>>>'))
            child.sendline('from album.runner.api import get_environment_path')
            self.assertEqual(0, child.expect(r'>>>'))
            child.sendline('print(get_environment_path())')
            self.assertEqual(0, child.expect(r'catalog_local_group_name_0.1.0'))
            child.sendline('exit()')
            child.close()
        else:
            cmd = ['album', 'repl', self.get_test_solution_path()]
            p = subprocess.Popen(cmd, env=env, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p.communicate(b"exit()\r")
            self.assertEqual(0, p.returncode)


if __name__ == '__main__':
    unittest.main()

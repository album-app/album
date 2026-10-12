import os
import re
import subprocess
import sys
from test.integration.test_integration_core_common import TestIntegrationCoreCommon


class TestIntegrationRepl(TestIntegrationCoreCommon):
    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    def test_repl(self):
        solution_path = self.get_test_solution_path("solution8_arguments.py")
        self.fake_install(solution_path)
        resolve_result = (
            self.album_controller.collection_manager().resolve_installed_and_load(
                solution_path
            )
        )
        environment = self.album_controller.environment_manager().set_environment(
            resolve_result
        )
        env = os.environ.copy()
        env["ALBUM_BASE_CACHE_PATH"] = str(
            self.album_controller.configuration().base_cache_path()
        )

        # call - the REPL reads its input line by line, it needs no terminal
        process = subprocess.run(
            [sys.executable, "-m", "album", "repl", solution_path],
            env=env,
            input=b"from album.runner.api import get_environment_path\n"
            b"print('REPL', 'environment:', get_environment_path())\n"
            b"exit()\n",
            capture_output=True,
            timeout=600,
        )

        # assert - the REPL ran in the environment of the solution
        output = (process.stdout + process.stderr).decode(errors="replace")
        self.assertEqual(0, process.returncode, output)
        self.assertEqual(
            [str(environment.path())],
            re.findall(r"REPL environment: (.*?)\r?$", output, re.MULTILINE),
            output,
        )

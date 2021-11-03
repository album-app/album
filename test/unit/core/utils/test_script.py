import threading
import unittest
from logging import StreamHandler
from unittest.mock import MagicMock

from album.core.controller.conda_manager import CondaManager
from album.core.utils.script import create_script
from album.runner import logging
from test.unit.test_unit_common import TestUnitCommon


class TestScript(TestUnitCommon):

    def setUp(self):
        super().setUp()
        self.create_album_test_instance(init_catalogs=False)
        self.conda = CondaManager()

    def tearDown(self):
        self.conda = None
        super().tearDown()

    @unittest.skip("Needs to be implemented!")
    def test_create_solution_script(self):
        # ToDo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def create_solution_with_parent_script(self):
        # ToDo: implement
        pass

    def test_create_script(self):
        script = create_script("script-test", "print(\"testprint\\n\")", [])
        with open(self.closed_tmp_file.name, "w") as f:
            f.writelines(script)

        # execute script
        p = self.conda.get_active_environment_path()
        self.conda.run_script(p, self.closed_tmp_file.name)

        self.assertIn("root.unitTest.script-test - INFO - testprint", self.captured_output.getvalue())

    def test_run_logging_from_thread(self):
        thread = threading.Thread(target=self._run_in_thread, args=(threading.current_thread().ident, ))
        thread.start()
        thread.join()

    def _run_in_thread(self, parent_thread_id):
        logging.configure_logging("thread", parent_thread_id=parent_thread_id)

        handler = StreamHandler()
        self.logger.addHandler(handler)

        script = create_script("script-test", "print(\"testprint\")", [])
        with open(self.closed_tmp_file.name, "w") as f:
            f.writelines(script)

        p = self.conda.get_active_environment_path()
        self.conda.run_script(p, self.closed_tmp_file.name)

        self.assertIn("root.unitTest.thread.script-test - INFO - testprint", self.captured_output.getvalue())


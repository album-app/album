import unittest
from io import StringIO

from hips.core.model.environment import Conda
from hips.core.model.hips_base import HipsClass


class TestHipsBase(unittest.TestCase):

    def tearDown(self) -> None:
        Conda.remove_environment("unit-test-env")

    test_environment_yml = StringIO("""name: unit-test-env
channels:
  - conda-forge
  - defaults
""")

    def test_init_(self):
        HipsClass({
            "group": "gr1",
            "version": "v1",
            "name": "n1",
            "min_hips_version": "1",
            "dependencies": {'environment_file': self.test_environment_yml}
        })

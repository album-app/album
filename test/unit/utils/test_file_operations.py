import pathlib
import tempfile
import unittest.mock
from unittest.mock import patch

from utils.file_operations import *


class TestUtilsFileOperations(unittest.TestCase):

    def setUp(self):
        self.set_dummy_solution_path()

    def set_dummy_solution_path(self):
        current_path = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))
        self.dummysolution = str(current_path.joinpath("..", "..", "resources", "dummysolution.py"))

    def test_get_zenodo_metadata(self):
        doi = get_zenodo_metadata(self.dummysolution, "doi")
        self.assertEqual("", doi)

    def test_get_zenodo_metadata_wrong_format(self):
        file = tempfile.NamedTemporaryFile(mode='w+', delete=False)

        with open(self.dummysolution) as d:
            l = d.readlines()
            file.writelines([x.replace(" ", "") for x in l])
        file.close()

        with self.assertRaises(FileOperationError):
            get_zenodo_metadata(file.name, "doi")

        os.remove(file.name)

    def test_get_zenodo_metadata_no_doi(self):
        file = tempfile.NamedTemporaryFile(mode='w+', delete=False)

        with open(self.dummysolution) as d:
            l = d.readlines()
            l.remove("    doi=\"\",\n")
            file.writelines(l)
        file.close()

        self.assertIsNone(get_zenodo_metadata(file.name, "doi"))

        os.remove(file.name)

    @patch('utils.file_operations.shutil.copy', return_value=True)
    def test_set_zenodo_metadata_in_solutionfile(self, shutil_mock):
        file_path = set_zenodo_metadata_in_solutionfile(self.dummysolution, "theDoi", "theID")

        with open(file_path) as f:
            l = f.readlines()
            self.assertIn("    doi=\"\",\n", l)
            self.assertIn("    deposit_id=\"\",\n", l)

        new_file_path = str(xdg_cache_home().joinpath("dummysolution_tmp.py"))

        with open(new_file_path) as f:
            l = f.readlines()
            self.assertIn("    doi=\"theDoi\",\n", l)
            self.assertNotIn("    doi=\"\",\n", l)
            self.assertIn("    deposit_id=\"theID\",\n", l)
            self.assertNotIn("    deposit_id=\"\",\n", l)

        shutil_mock.assert_called_once()

        os.remove(new_file_path)

    @patch('utils.file_operations.shutil.copy', return_value=True)
    def test_set_zenodo_metadata_in_solutionfile_wrong_format(self, shutil_mock):
        file = tempfile.NamedTemporaryFile(mode='w+', delete=False)

        with open(self.dummysolution) as d:
            l = d.readlines()
            file.writelines([x.replace(" ", "") for x in l])
        file.close()

        with self.assertRaises(FileOperationError):
            set_zenodo_metadata_in_solutionfile(file.name, "theDoi", "theID")

        shutil_mock.assert_not_called()
        os.remove(file.name)


if __name__ == '__main__':
    unittest.main()

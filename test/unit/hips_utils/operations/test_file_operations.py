import os
import pathlib
import shutil
import tempfile
import unittest.mock
from unittest.mock import patch

from xdg import xdg_cache_home

from hips_utils.operations.file_operations import FileOperationError, get_zenodo_metadata, \
    set_zenodo_metadata_in_solutionfile, get_dict_from_yml, write_dict_to_yml, create_empty_file_recursively, \
    create_path_recursively


class TestFileOperations(unittest.TestCase):

    def setUp(self):
        self.set_dummy_solution_path()

    def tearDown(self) -> None:
        try:
            pathlib.Path(tempfile.gettempdir()).joinpath("test_yaml").unlink()
        except FileNotFoundError:
            pass
        shutil.rmtree(pathlib.Path(tempfile.gettempdir()).joinpath("test_folder"), ignore_errors=True)

    def set_dummy_solution_path(self):
        current_path = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))
        self.dummysolution = str(current_path.joinpath("..", "..", "..", "resources", "dummysolution.py"))

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

    @patch('hips_utils.operations.file_operations.shutil.copy', return_value=True)
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

    @patch('hips_utils.operations.file_operations.shutil.copy', return_value=True)
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

    def test_get_dict_from_yml(self):
        tmp_folder = pathlib.Path(tempfile.gettempdir())

        tmp_yml_file = tmp_folder.joinpath("test_yaml")
        with open(tmp_yml_file, "w+") as f:
            f.write("test: [1, 2, 3]")

        d = get_dict_from_yml(tmp_yml_file)
        self.assertEqual(d, {"test": [1, 2, 3]})

    def test_write_dict_to_yml(self):
        self.tearDown()
        tmp_yml_file = pathlib.Path(tempfile.gettempdir()).joinpath("test_yaml")
        tmp_yml_file.touch()
        self.assertEqual(tmp_yml_file.stat().st_size, 0)
        d = {"test": [1, 2, 3]}
        write_dict_to_yml(tmp_yml_file, d)
        self.assertTrue(tmp_yml_file.stat().st_size > 0)

    def test_create_empty_file_recursively(self):
        tmp_dir = pathlib.Path(tempfile.gettempdir())
        tmp_file = tmp_dir.joinpath("test_folder", "new_folder", "t.txt")

        create_empty_file_recursively(tmp_file)

        self.assertTrue(tmp_file.is_file())
        self.assertTrue(tmp_file.parent.is_dir())
        self.assertEqual(tmp_file.stat().st_size, 0)

    def test_create_empty_file_recursively_no_overwrite(self):
        tmp_dir = pathlib.Path(tempfile.gettempdir())
        tmp_file = tmp_dir.joinpath("test_folder", "new_folder", "t.txt")

        self.test_create_empty_file_recursively()

        with open(tmp_file, "w") as f:
            f.write("test")

        self.assertNotEqual(tmp_file.stat().st_size, 0)

        # create a file which already exists
        create_empty_file_recursively(tmp_file)

        # content should still be the same!
        self.assertNotEqual(tmp_file.stat().st_size, 0)

    def test_create_path_recursively(self):
        tmp_dir = pathlib.Path(tempfile.gettempdir())
        tmp_folder = tmp_dir.joinpath("test_folder", "new_folder")

        self.assertFalse(tmp_folder.is_dir())

        create_path_recursively(tmp_folder)

        self.assertTrue(tmp_folder.is_dir())


if __name__ == '__main__':
    unittest.main()

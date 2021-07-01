import json
import os
import pathlib
import unittest.mock
from pathlib import Path
from stat import *
from unittest.mock import patch

from hips.core.model.default_values import HipsDefaultValues
from hips.core.utils.operations.file_operations import FileOperationError, get_zenodo_metadata, \
    set_zenodo_metadata_in_solutionfile, get_dict_from_yml, write_dict_to_yml, create_empty_file_recursively, \
    create_path_recursively, write_dict_to_json, remove_warning_on_error, zip_folder, unzip_archive, copy, \
    copy_folder, zip_paths

from test.unit.test_common import TestHipsCommon


class TestFileOperations(TestHipsCommon):

    def setUp(self):
        self.set_dummy_solution_path()

    def tearDown(self) -> None:
        super().tearDown()

    def set_dummy_solution_path(self):
        current_path = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))
        self.dummysolution = str(current_path.joinpath("..", "..", "..", "..", "resources", "solution0_dummy.py"))

    def test_get_zenodo_metadata(self):
        doi = get_zenodo_metadata(self.dummysolution, "doi")
        self.assertEqual("", doi)

    def test_get_zenodo_metadata_wrong_format(self):

        with open(self.closed_tmp_file.name, mode="w") as file:
            with open(self.dummysolution) as d:
                lines = d.readlines()
                file.writelines([x.replace(" ", "") for x in lines])

        with self.assertRaises(FileOperationError):
            get_zenodo_metadata(self.closed_tmp_file.name, "doi")

    def test_get_zenodo_metadata_no_doi(self):
        with open(self.closed_tmp_file.name, mode="w") as file:
            with open(self.dummysolution) as d:
                lines = d.readlines()
                lines.remove("    doi=\"\",\n")
                file.writelines(lines)

        self.assertIsNone(get_zenodo_metadata(self.closed_tmp_file.name, "doi"))

    @patch('hips.core.utils.operations.file_operations.shutil.copy', return_value=True)
    def test_set_zenodo_metadata_in_solutionfile(self, shutil_mock):
        file_path = set_zenodo_metadata_in_solutionfile(self.dummysolution, "theDoi", "theID")

        with open(file_path) as f:
            lines = f.readlines()
            self.assertIn("    doi=\"\",\n", lines)
            self.assertIn("    deposit_id=\"\",\n", lines)

        # needs to be this path - see @set_zenodo_metadata_in_solutionfile
        new_file_path = str(HipsDefaultValues.app_cache_dir.value.joinpath("solution0_dummy_tmp.py"))

        with open(new_file_path) as f:
            lines = f.readlines()
            self.assertIn("    doi=\"theDoi\",\n", lines)
            self.assertNotIn("    doi=\"\",\n", lines)
            self.assertIn("    deposit_id=\"theID\",\n", lines)
            self.assertNotIn("    deposit_id=\"\",\n", lines)

        shutil_mock.assert_called_once()

    @patch('hips.core.utils.operations.file_operations.shutil.copy', return_value=True)
    def test_set_zenodo_metadata_in_solutionfile_wrong_format(self, shutil_mock):
        with open(self.closed_tmp_file.name, mode="w") as file:
            with open(self.dummysolution) as d:
                lines = d.readlines()
                file.writelines([x.replace(" ", "") for x in lines])

        with self.assertRaises(FileOperationError):
            set_zenodo_metadata_in_solutionfile(self.closed_tmp_file.name, "theDoi", "theID")

        shutil_mock.assert_not_called()

    def test_get_dict_from_yml(self):
        tmp_folder = pathlib.Path(self.tmp_dir.name)

        tmp_yml_file = tmp_folder.joinpath("test_yaml")
        with open(tmp_yml_file, "w+") as f:
            f.write("test: [1, 2, 3]")

        d = get_dict_from_yml(tmp_yml_file)
        self.assertEqual(d, {"test": [1, 2, 3]})

    def test_write_dict_to_yml(self):
        tmp_yml_file = pathlib.Path(self.tmp_dir.name).joinpath("test_yaml")
        tmp_yml_file.touch()
        self.assertEqual(tmp_yml_file.stat().st_size, 0)
        d = {"test": [1, 2, 3]}
        write_dict_to_yml(tmp_yml_file, d)
        self.assertTrue(tmp_yml_file.stat().st_size > 0)

    def test_write_dict_to_json(self):
        # named "yaml" here because tearDown() deletes it automatically, but that does not matter here
        tmp_json_file = pathlib.Path(self.tmp_dir.name).joinpath("test_yaml")
        tmp_json_file.touch()
        self.assertEqual(tmp_json_file.stat().st_size, 0)
        d = {"test": [1, 2, 3]}
        write_dict_to_json(tmp_json_file, d)
        self.assertTrue(tmp_json_file.stat().st_size > 0)
        d_loaded = json.load(open(tmp_json_file))
        self.assertEqual(d_loaded, d)

    def test_create_empty_file_recursively(self):
        tmp_file = pathlib.Path(self.tmp_dir.name).joinpath("test_folder", "new_folder", "t.txt")

        create_empty_file_recursively(tmp_file)

        self.assertTrue(tmp_file.is_file())
        self.assertTrue(tmp_file.parent.is_dir())
        self.assertEqual(tmp_file.stat().st_size, 0)

    def test_create_empty_file_recursively_no_overwrite(self):
        tmp_dir = pathlib.Path(self.tmp_dir.name)
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
        tmp_dir = pathlib.Path(self.tmp_dir.name)
        tmp_folder = tmp_dir.joinpath("test_folder", "new_folder")

        self.assertFalse(tmp_folder.is_dir())

        create_path_recursively(tmp_folder)

        self.assertTrue(tmp_folder.is_dir())

    def test_copy_folder(self):
        tmp_dir = pathlib.Path(self.tmp_dir.name)

        # source
        source_copy = tmp_dir.joinpath("test_to_copy_folder")
        create_path_recursively(source_copy)

        source_copy_file_a = source_copy.joinpath("aFile.txt")
        source_copy_file_a.touch()

        source_copy_folder_inside = source_copy.joinpath("a_new_folder")
        create_path_recursively(source_copy_folder_inside)

        source_copy_file_b = source_copy_folder_inside.joinpath("bFile.txt")
        source_copy_file_b.touch()

        # target
        target_copy = tmp_dir.joinpath("test_copy_target_folder")

        # copy without root
        copy_folder(source_copy, target_copy, copy_root_folder=False)

        self.assertTrue(target_copy.joinpath("a_new_folder", "bFile.txt").exists())
        self.assertTrue(target_copy.joinpath("aFile.txt").exists())

        # copy with root
        target_copy = tmp_dir.joinpath("test_copy_target_folder_with_root")

        copy_folder(source_copy, target_copy, copy_root_folder=True)

        self.assertTrue(target_copy.joinpath(source_copy.name, "a_new_folder", "bFile.txt").exists())
        self.assertTrue(target_copy.joinpath(source_copy.name, "aFile.txt").exists())

    def test_copy(self):
        tmp_dir = pathlib.Path(self.tmp_dir.name)

        # source
        source_copy = tmp_dir.joinpath("test_to_copy_folder")
        create_path_recursively(source_copy)
        source_copy_file = source_copy.joinpath("aFile.txt")
        source_copy_file.touch()

        # target
        target_copy = tmp_dir.joinpath("test_unzip_target_folder")
        create_path_recursively(target_copy)

        # copy
        copy(source_copy_file, target_copy)  # to new target folder
        copy(source_copy_file, target_copy.joinpath("newname.txt"))  # to new target folder with new name

        # assert
        self.assertTrue(target_copy.joinpath("aFile.txt"))
        self.assertTrue(target_copy.joinpath("newname.txt"))

    def test_zip_folder(self):
        tmp_dir = pathlib.Path(self.tmp_dir.name)
        source_dir = tmp_dir.joinpath("test_source_folder")
        create_path_recursively(source_dir)

        tmp_file = source_dir.joinpath("aFile.txt")
        tmp_file.touch()

        target_zip = tmp_dir.joinpath("test_target_folder", "anArchive.zip")

        # archive
        zip_folder(source_dir, target_zip)

        self.assertTrue(target_zip.exists())

    def test_zip_paths(self):
        tmp_dir = pathlib.Path(self.tmp_dir.name)
        source_dir = tmp_dir.joinpath("test_source_folder1")
        create_path_recursively(source_dir)

        source_dir2 = tmp_dir.joinpath("test_source_folder2")
        create_path_recursively(source_dir2)

        source_dir.joinpath("aFile.txt").touch()

        tmp_file = source_dir2.joinpath("bFile.txt")
        tmp_file.touch()

        target_zip = tmp_dir.joinpath("test_target_folder", "anArchive.zip")

        target_unzip = tmp_dir.joinpath("test_unzip_target_folder")
        create_path_recursively(target_unzip)

        # archive
        zip_paths([source_dir, tmp_file], target_zip)

        # unzip
        unzip_archive(target_zip, target_unzip)

        # check
        self.assertTrue(target_unzip.joinpath("test_source_folder1").exists())
        self.assertTrue(target_unzip.joinpath("test_source_folder1", "aFile.txt").exists())
        self.assertTrue(target_unzip.joinpath("bFile.txt").exists())


    def test_unzip_archive(self):
        tmp_dir = pathlib.Path(self.tmp_dir.name)
        source_dir = tmp_dir.joinpath("test_source_folder")
        create_path_recursively(source_dir)

        tmp_file = source_dir.joinpath("aFile.txt")
        tmp_file.touch()

        target_zip = tmp_dir.joinpath("test_target_folder", "anArchive.zip")

        target_unzip = tmp_dir.joinpath("test_unzip_target_folder")
        create_path_recursively(target_unzip)

        # archive
        zip_folder(source_dir, target_zip)

        # unzip
        unzip_archive(target_zip, target_unzip)

        # assert
        self.assertTrue(target_unzip.joinpath("aFile.txt").exists())

    def test_remove_warning_on_error_no_folder(self):
        p = Path(self.tmp_dir.name).joinpath("not_exist")

        remove_warning_on_error(p)

        self.assertIn("No content in ", self.captured_output.getvalue())

    def test_remove_warning_on_error_folder_undeletable(self):
        p = Path(self.tmp_dir.name).joinpath("folder_in_use")

        create_path_recursively(p)

        f = p.joinpath("strange_file.txt")
        with open(str(f), 'w+') as fp:
            fp.write("test\n")

        # make file and folder user-read-only.
        os.chmod(p, S_IREAD)

        # un-deletable
        try:
            skip = True
            f.unlink()
        except PermissionError:
            skip = False

            # no error and folder deleted
            self.assertIsNone(remove_warning_on_error(p))
            self.assertFalse(p.exists())

        if skip:
            self.skipTest("Cannot setup test routine. Unknown reason!")


if __name__ == '__main__':
    unittest.main()

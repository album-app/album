import json
import os
import pathlib
import stat
import unittest.mock
from pathlib import Path

from album.core.utils.operations.file_operations import get_dict_from_yml, write_dict_to_yml, \
    create_empty_file_recursively, \
    create_path_recursively, write_dict_to_json, force_remove, zip_folder, unzip_archive, copy, \
    copy_folder, zip_paths, rand_folder_name, folder_empty
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestFileOperations(TestUnitCoreCommon):

    def setUp(self):
        super().setUp()
        self.set_dummy_solution_path()

    def tearDown(self) -> None:
        super().tearDown()

    def set_dummy_solution_path(self):
        current_path = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))
        self.dummysolution = str(current_path.joinpath("..", "..", "..", "..", "resources", "solution0_dummy.py"))

    def test_get_dict_from_yml(self):
        tmp_folder = pathlib.Path(self.tmp_dir.name)

        tmp_yml_file = tmp_folder.joinpath("test_yaml")
        with open(tmp_yml_file, "w+") as f:
            f.write("test: [1, 2, 3]")

        d = get_dict_from_yml(tmp_yml_file)
        self.assertEqual(d, {"test": [1, 2, 3]})

    def test_get_dict_from_yml_string_only(self):
        tmp_folder = pathlib.Path(self.tmp_dir.name)

        tmp_yml_file = tmp_folder.joinpath("test_yaml")
        with open(tmp_yml_file, "w+") as f:
            f.write("iAmOnlyAString")

        with self.assertRaises(TypeError):
            get_dict_from_yml(tmp_yml_file)

    def test_get_dict_from_yml_empty(self):
        tmp_folder = pathlib.Path(self.tmp_dir.name)

        tmp_yml_file = tmp_folder.joinpath("test_yaml")
        tmp_yml_file.touch()

        with self.assertRaises(TypeError):
            get_dict_from_yml(tmp_yml_file)

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

    def test_folder_empty(self):
        self.assertTrue(folder_empty(Path(self.tmp_dir.name).joinpath("myFolder")))
        p = Path(self.tmp_dir.name).joinpath("myFolder")
        p.mkdir()
        self.assertTrue(folder_empty(p))
        p.joinpath("myfile.txt").touch()
        self.assertFalse(folder_empty(p))

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
        self.assertTrue(target_copy.joinpath("aFile.txt").exists())
        self.assertTrue(target_copy.joinpath("newname.txt").exists())

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
        r = zip_paths([source_dir, tmp_file], target_zip, tmp_dir=tmp_dir)
        self.assertEqual(str(target_zip), r)

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
        r = zip_folder(source_dir, target_zip)
        self.assertEqual(str(target_zip), r)

        # unzip
        unzip_archive(target_zip, target_unzip)

        # assert
        self.assertTrue(target_unzip.joinpath("aFile.txt").exists())

    def test_force_remove_no_folder(self):
        p = Path(self.tmp_dir.name).joinpath("not_exist")

        force_remove(p)

    def test_force_remove_file(self):
        p = Path(self.tmp_dir.name).joinpath("file_exist")
        p.touch()

        force_remove(p)

    def test_force_remove_file_permission_error(self):
        p = Path(self.tmp_dir.name).joinpath("file_exist")

        # make file protected and check if fallback is executed
        p.touch()
        os.chmod(p, stat.S_IWRITE)  # make write protected

        force_remove(p)  # should not fail

    def test_rand_folder_name(self):
        f1 = rand_folder_name()
        f2 = rand_folder_name(f_len=10)

        self.assertEqual(8, len(f1))
        self.assertEqual(10, len(f2))


if __name__ == '__main__':
    unittest.main()

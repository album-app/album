import copy
import os
import tempfile
import unittest

from requests import Response

from hips.ci.zenodo_api import ZenodoEntry, ZenodoMetadata, ZenodoFile, ZenodoDeposit, UploadType, IterableList, \
    InvalidResponseStatusError, ZenodoAPI, ResponseStatus
from test.unit.test_common import TestZenodoCommon


class TestZenodoEntry(unittest.TestCase):

    def test_to_to_dict(self):
        init_dict = {"test": "test_value"}
        base_url = "'https://test.test/'"
        access_token = "1234567890"

        test_entry_1 = ZenodoEntry(init_dict, base_url, access_token)

        self.assertTrue(test_entry_1.to_dict() == {})


class TestZenodoDeposit(TestZenodoCommon):

    def setUp(self):
        self.init_dict = {
            "metadata": ZenodoMetadata({"title": "unit_test"}).__dict__,
            "files": [
                ZenodoFile({"filename": "test_file_1", "id": 1}).__dict__,
                ZenodoFile({"filename": "test_file_2", "id": 2}).__dict__,
            ],
        }
        self.test_offline_zenodo_deposit = ZenodoDeposit(self.init_dict, self.base_url, self.access_token)

    def test_get_files_id_by_name(self):
        self.assertTrue(self.test_offline_zenodo_deposit.get_files_id_by_name("test_file_2") == 2)

    def test_list_files_name(self):
        self.assertTrue(self.test_offline_zenodo_deposit.list_files_name() == ["test_file_1", "test_file_2"])

    def test_reload(self):
        altered_deposit = copy.deepcopy(self.test_deposit)
        altered_deposit.owner = "Test"

        self.assertFalse(altered_deposit.owner == self.test_deposit.owner)

        altered_deposit.reload()

        self.assertEqual(altered_deposit.owner, self.test_deposit.owner)

    def test_update(self):
        zenodo_metadata = ZenodoMetadata({
            "title": "unit_test",
            "description": "test",
            "upload_type": UploadType.SOFTWARE.value,
            "creators": [{"name": "UnitTestCi", "affiliation": 'UnitTestMDC'}]
        })
        old_metadata = self.test_deposit.metadata

        self.test_deposit.update(zenodo_metadata)

        self.assertNotEqual(old_metadata, self.test_deposit.metadata)

    @unittest.skip("Unit testing based on this method. Is indirectly tested")
    def test_delete(self):
        pass

    # ToDo: discuss what to do
    @unittest.skip("Would publish the result. Remains untested")
    def test_publish(self):
        pass

    # ToDo: discuss what to do
    @unittest.skip("Needs to be published. Remains untested")
    def test_new_version(self):
        pass

    @unittest.skip("Tested in \'test_create_file\'. Will skip!")
    def test_get_remote_files(self):
        pass

    def test_create_file(self):
        # file is not allowed to end with "_" character for reasons. This solution is ugly but works...
        while True:
            file = tempfile.NamedTemporaryFile(mode='w+')
            if not file.name.endswith("_"):
                break
        file.write('test')
        file.flush()
        os.fsync(file)

        self.test_deposit.create_file(file.name)

        self.assertEqual(self.test_deposit.files[0].filename, os.path.basename(file.name))

        file.close()

    def test_delete_file(self):
        # file is not allowed to end with "_" character for reasons. This solution is ugly but works...
        while True:
            file = tempfile.NamedTemporaryFile(mode='w+')
            if not file.name.endswith("_"):
                break
        file.write('test')
        file.flush()
        os.fsync(file)

        parsed_name, ext = os.path.splitext(os.path.basename(file.name))
        expected_file_name = parsed_name + ext

        self.test_deposit.create_file(file.name)
        self.assertEqual(expected_file_name, self.test_deposit.files[expected_file_name].filename)
        self.assertEqual(len(self.test_deposit.files), 1)

        self.test_deposit.delete_file(os.path.basename(file.name))

        self.assertIsInstance(self.test_deposit.files, IterableList)
        self.assertEqual(len(self.test_deposit.files), 0)

    def test_update_file(self):
        # file is not allowed to end with "_" character for reasons. This solution is ugly but works...
        while True:
            file = tempfile.NamedTemporaryFile(mode='w+')
            if not file.name.endswith("_"):
                break
        file_name = os.path.basename(file.name)
        file.write('test')
        file.flush()
        os.fsync(file)

        self.test_deposit.create_file(file.name)
        self.assertEqual(1, len(self.test_deposit.files))
        self.assertEqual(file_name, self.test_deposit.files[0].filename)

        file_new = tempfile.NamedTemporaryFile(mode='w+')
        file_new.write('test_new')
        file_new.flush()
        os.fsync(file_new)

        self.test_deposit.update_file(file_name, file_new.name)

        self.assertEqual(len(self.test_deposit.files), 1)
        self.assertEqual(self.test_deposit.files[0].filename, os.path.basename(file_new.name))

    @unittest.skip("Tested in \'test_update_file\'. Will skip!")
    def test_update_file_by_id(self):
        pass

    @unittest.skip("Tested in \'test_delete_file\'. Will skip!")
    def test_delete_file_by_id(self):
        pass


class TestZenodoRecord(unittest.TestCase):

    @unittest.skip("Needs to be implemented!")
    def test_print_stats(self):
        # ToDo: implement
        pass


class TestZenodoAPI(TestZenodoCommon):

    def test_validate_response(self):
        response = Response()
        response.status_code = 200
        response._content = b'{\"test\":\"test_value\"}'

        # case OK, Accepted, Created - different status expected
        with self.assertRaises(InvalidResponseStatusError) as context:
            ZenodoAPI.validate_response(response, ResponseStatus.NoContent)
        self.assertTrue("Expected NoContent got OK" in str(context.exception))

        # case OK
        self.assertDictEqual({"test": "test_value"}, ZenodoAPI.validate_response(response, ResponseStatus.OK))

        # case Accepted
        response.status_code = ResponseStatus.Accepted.value
        self.assertDictEqual({"test": "test_value"}, ZenodoAPI.validate_response(response, ResponseStatus.Accepted))

        # case Created
        response.status_code = ResponseStatus.Created.value
        self.assertDictEqual({"test": "test_value"}, ZenodoAPI.validate_response(response, ResponseStatus.Created))

        # case NoContent
        response.status_code = ResponseStatus.NoContent.value
        self.assertTrue(bool(ZenodoAPI.validate_response(response, ResponseStatus.NoContent)))

        # case NoContent - different status expected
        with self.assertRaises(InvalidResponseStatusError) as context:
            ZenodoAPI.validate_response(response, ResponseStatus.OK)
        self.assertTrue("Expected OK got NoContent" in str(context.exception))

        # case InternalServerError
        response.status_code = ResponseStatus.InternalServerError.value
        with self.assertRaises(InvalidResponseStatusError) as context:
            ZenodoAPI.validate_response(response, ResponseStatus.InternalServerError)
        self.assertTrue(
            "Error \'%s\' occurred. See Log for detailed information!" % ResponseStatus.InternalServerError.name in str(
                context.exception))

    def test_deposit_get(self):
        self.assertEqual(self.test_deposit.id, self.zenodoAPI.deposit_get(self.test_deposit.id)[0].id)

    @unittest.skip("Unit testing based on this method. Is indirectly tested")
    def test_deposit_create(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_records_get(self):
        # ToDo: implement
        pass

    def test_deposit_create_with_prereserve_doi(self):

        title = "unit_test_solution.py"

        self.test_deposit2 = self.zenodoAPI.deposit_create_with_prereserve_doi(title)

        self.assertIsNot(self.test_deposit2.id, "", "ID empty string!")
        self.assertIsNot(self.test_deposit2.metadata.prereserve_doi["doi"], "", "doi empty string!")
        self.assertIsNotNone(self.test_deposit2.id, "ID of deposit not set!")
        self.assertIsNotNone(self.test_deposit2.metadata.prereserve_doi["doi"], "doi of deposit not set!")


if __name__ == '__main__':
    unittest.main()

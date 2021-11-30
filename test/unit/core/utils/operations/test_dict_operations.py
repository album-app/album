from album.core.utils.operations.dict_operations import get_dict_entries_from_attribute_path
from test.unit.test_unit_common import TestUnitCommon


class TestDictOperations(TestUnitCommon):
    
    def test_get_dict_entries_from_path(self):
        input = {
            'covers': [
                {
                    'source': 's1'
                }, {
                    'source': ['s2', 's3']
                }
            ]
        }
        output = get_dict_entries_from_attribute_path(input, 'covers.source')
        self.assertEqual(['s1', 's2', 's3'], output)

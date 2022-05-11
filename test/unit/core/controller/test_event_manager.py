import unittest
from unittest.mock import MagicMock

from album.core.model.event import Event
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestEventManager(TestUnitCoreCommon):

    def test_add_remove_publish(self):
        callback = MagicMock()
        self.album_controller.event_manager().add_listener('my-event', callback)
        self.album_controller.event_manager().publish(Event('my-event'))
        callback.assert_called_once()
        self.album_controller.event_manager().publish(Event('my-other-event'))
        callback.assert_called_once()
        self.album_controller.event_manager().remove_listener('my-event', callback)
        self.album_controller.event_manager().publish(Event('my-event'))
        callback.assert_called_once()


if __name__ == '__main__':
    unittest.main()

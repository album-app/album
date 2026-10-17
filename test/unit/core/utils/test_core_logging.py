import logging
import os
import unittest
from io import StringIO
from unittest.mock import patch

from album.core.utils.core_logging import ProgressIntervalFilter, ProgressLineHandler
from album.core.utils.operations.view_operations import get_logging_formatter


def _record(message, progress=False, level=logging.INFO):
    record = logging.makeLogRecord(
        {"msg": message, "levelno": level, "levelname": logging.getLevelName(level)}
    )
    if progress:
        record.album_progress = True
    return record


@patch(
    "album.core.utils.core_logging.shutil.get_terminal_size",
    return_value=os.terminal_size((10, 24)),
)
class TestProgressLineHandler(unittest.TestCase):
    def test_emit(self, _):
        stream = StringIO()
        handler = ProgressLineHandler(stream)

        handler.handle(_record("loading"))
        handler.handle(_record("50%", progress=True))
        handler.handle(_record("100% of 2", progress=True))
        handler.handle(_record("100%"))
        handler.handle(_record("done"))

        # each record first erases the progress update before it
        self.assertEqual(
            "loading\n50%\r\x1b[J100% of 2\r\x1b[J100%\ndone\n", stream.getvalue()
        )

    def test_emit_progress_over_several_rows(self, _):
        stream = StringIO()
        handler = ProgressLineHandler(stream)

        handler.handle(_record("0123456789abc", progress=True))
        handler.handle(_record("0123456789", progress=True))
        handler.handle(_record("done"))

        # an update wider than the terminal is written whole, the next record moves
        # back up to its first row; one that fills its last row gets a space
        self.assertEqual(
            "0123456789abc\r\x1b[1A\x1b[J0123456789 \r\x1b[1A\x1b[Jdone\n",
            stream.getvalue(),
        )

    def test_emit_progress_without_colour_codes(self, _):
        stream = StringIO()
        handler = ProgressLineHandler(stream)
        handler.setFormatter(get_logging_formatter(fmt="%(log_color)s%(message)s"))

        handler.handle(_record("50%", progress=True, level=logging.WARNING))

        self.assertEqual("50%", stream.getvalue())


class TestProgressIntervalFilter(unittest.TestCase):
    @patch(
        "album.core.utils.core_logging.time.monotonic",
        side_effect=[100.0, 110.0, 131.0],
    )
    def test_filter(self, _):
        progress_filter = ProgressIntervalFilter(30)

        passed = [
            progress_filter.filter(_record(message, progress=True))
            for message in ("0%", "50%", "100%")
        ]

        self.assertEqual([True, False, True], passed)
        self.assertTrue(progress_filter.filter(_record("done")))


if __name__ == "__main__":
    unittest.main()

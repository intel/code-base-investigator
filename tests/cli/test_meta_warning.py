# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import re
import unittest

from codebasin.cli import MetaWarning


class TestMetaWarning(unittest.TestCase):
    """
    Test MetaWarning class.
    """

    def test_constructor(self):
        """Check constructor arguments"""
        mw = MetaWarning("regex", "msg")
        self.assertTrue(mw.regex, re.compile("regex"))
        self.assertTrue(mw.msg, "msg")
        self.assertEqual(mw._count, 0)

    def test_inspect(self):
        """Check inspect matches records correctly"""
        mw = MetaWarning("test[0-9]", "Testing")

        record = logging.makeLogRecord(
            {
                "msg": "test1",
                "levelname": "WARNING",
            },
        )
        self.assertTrue(mw.inspect(record))
        self.assertEqual(mw._count, 1)

        record = logging.makeLogRecord(
            {
                "msg": "testA",
                "levelname": "WARNING",
            },
        )
        self.assertFalse(mw.inspect(record))
        self.assertEqual(mw._count, 1)

    def test_warn(self):
        """Check warn produces expected logging messages"""
        logging.disable(logging.NOTSET)
        logger = logging.getLogger("codebasin")

        mw = MetaWarning("test[0-9]", "Testing {}")
        with self.assertNoLogs(logger):
            mw.warn(logger)

        record = logging.makeLogRecord(
            {
                "msg": "test1",
                "levelno": logging.WARNING,
            },
        )
        mw.inspect(record)
        with self.assertLogs(logger, level="WARNING") as cm:
            mw.warn(logger)
        self.assertEqual(cm.output, ["WARNING:codebasin:Testing 1"])
        logging.disable()


if __name__ == "__main__":
    unittest.main()

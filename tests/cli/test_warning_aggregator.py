# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import unittest

from codebasin._detail.logging import WarningAggregator


class TestWarningAggregator(unittest.TestCase):
    """
    Test WarningAggregator class.
    """

    def test_constructor(self):
        """Check constructor arguments"""
        wa = WarningAggregator()
        self.assertEqual(len(wa.meta_warnings), 3)

    def test_filter(self):
        """Check filter inspects warnings correctly"""
        wa = WarningAggregator()
        record = logging.makeLogRecord(
            {
                "msg": "test1",
                "levelname": "WARNING",
                "levelno": logging.WARNING,
            },
        )
        self.assertTrue(wa.filter(record))
        self.assertEqual(wa.meta_warnings[0]._count, 1)
        self.assertEqual(wa.meta_warnings[1]._count, 0)
        self.assertEqual(wa.meta_warnings[2]._count, 0)

        record = logging.makeLogRecord(
            {
                "msg": "Missing user include",
                "levelname": "WARNING",
                "levelno": logging.WARNING,
            },
        )
        self.assertTrue(wa.filter(record))
        self.assertEqual(wa.meta_warnings[0]._count, 2)
        self.assertEqual(wa.meta_warnings[1]._count, 1)
        self.assertEqual(wa.meta_warnings[2]._count, 0)

        record = logging.makeLogRecord(
            {
                "msg": "Missing system include",
                "levelname": "WARNING",
                "levelno": logging.WARNING,
            },
        )
        self.assertTrue(wa.filter(record))
        self.assertEqual(wa.meta_warnings[0]._count, 3)
        self.assertEqual(wa.meta_warnings[1]._count, 1)
        self.assertEqual(wa.meta_warnings[2]._count, 1)

        # NB: This matches on message but not levelname.
        record = logging.makeLogRecord(
            {
                "msg": "Missing system include",
                "levelname": "ERROR",
                "levelno": logging.ERROR,
            },
        )
        self.assertTrue(wa.filter(record))
        self.assertEqual(wa.meta_warnings[0]._count, 3)
        self.assertEqual(wa.meta_warnings[1]._count, 1)
        self.assertEqual(wa.meta_warnings[2]._count, 1)

    def test_warn(self):
        """Check warn produces expected logging messages"""
        logging.disable(logging.NOTSET)
        logger = logging.getLogger("codebasin")

        wa = WarningAggregator()
        with self.assertNoLogs(logger):
            wa.warn(logger)

        wa.filter(
            logging.makeLogRecord(
                {
                    "msg": "test1",
                    "levelname": "WARNING",
                    "levelno": logging.WARNING,
                },
            ),
        )
        wa.filter(
            logging.makeLogRecord(
                {
                    "msg": "Missing user include",
                    "levelname": "WARNING",
                    "levelno": logging.WARNING,
                },
            ),
        )
        wa.filter(
            logging.makeLogRecord(
                {
                    "msg": "Missing system include",
                    "levelname": "WARNING",
                    "levelno": logging.WARNING,
                },
            ),
        )
        with self.assertLogs(logger, level="WARNING") as cm:
            wa.warn(logger)

        self.assertRegex(cm.output[0], "3 warnings generated")
        self.assertRegex(cm.output[1], "user include files")
        self.assertRegex(cm.output[2], "system include files")

        logging.disable()


if __name__ == "__main__":
    unittest.main()

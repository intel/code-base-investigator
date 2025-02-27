# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import unittest

from codebasin._detail.logging import Formatter


class TestFormatter(unittest.TestCase):
    """
    Test Formatter class.
    """

    def setUp(self):
        logging.disable()

    def test_constructor(self):
        """Check constructor arguments"""
        self.assertTrue(Formatter(colors=True).colors)
        self.assertFalse(Formatter(colors=False).colors)
        self.assertFalse(Formatter().colors)

    def test_format(self):
        """Check output format"""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        colors = ["\033[39m", "\033[39m", "\033[93m", "\033[91m"]
        for colorize in [True, False]:
            for levelname, color in zip(levels, colors):
                formatter = Formatter(colors=colorize)
                with self.subTest(
                    colorize=colorize,
                    levelname=levelname,
                    color=color,
                ):
                    record = logging.makeLogRecord(
                        {
                            "msg": "Testing",
                            "levelname": levelname,
                        },
                    )
                    msg = record.msg
                    level = record.levelname.lower()
                    output = formatter.format(record)
                    if level == "info":
                        expected = msg
                    elif colorize:
                        expected = f"\033[1m{color}{level}\033[0m: {msg}"
                    else:
                        expected = f"{level}: {msg}"
                    self.assertEqual(output, expected)


if __name__ == "__main__":
    unittest.main()

# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import unittest

from codebasin.report import _human_readable, _strip_colors


class TestFileTreeUtils(unittest.TestCase):
    """
    Test FileTree utility/helper functions.
    """

    def setUp(self):
        logging.disable()

    def test_human_readable_validation(self):
        """Check that human_readable rejects non-integers."""
        with self.assertRaises(TypeError):
            _ = _human_readable("1")

    def test_human_readable(self):
        """Check that human_readable produces correct results."""
        integers = [1, 12, 123, 1234, 12345, 123456, 123456789]
        strings = ["1", "12", "123", "1.2k", "12.3k", "123.5k", "123.5M"]
        for i, expected in zip(integers, strings):
            with self.subTest(i=i, expected=expected):
                s = _human_readable(i)
                self.assertEqual(s, expected)

    def test_strip_colors_validation(self):
        """Check that strip_colors rejects non-strings."""
        with self.assertRaises(TypeError):
            _ = _strip_colors(1)

    def test_strip_colors(self):
        """Check that strip_colors produces correct results."""
        inputs = ["\033[2mA\033[0m", "\033[1m\033[33mB\033[0m"]
        expected = ["A", "B"]
        for s, expected in zip(inputs, expected):
            with self.subTest(s=s, expected=expected):
                stripped = _strip_colors(s)
                self.assertEqual(stripped, expected)


if __name__ == "__main__":
    unittest.main()

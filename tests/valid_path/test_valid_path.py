# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import unittest

from codebasin import util


class TestValidPath(unittest.TestCase):
    """
    Test that valid_path correctly identifies null-byte, carriage return
    and line feed characters.
    """

    def test_valid(self):
        """Check that a valid path is accepted"""
        self.assertTrue(util.valid_path("/valid/path/"))

    def test_null_byte(self):
        """Check that a null-byte character is rejected"""
        self.assertFalse(util.valid_path("/invalid/\x00/path/"))

    def test_carriage_return(self):
        """Check that a carriage return character is rejected"""
        self.assertFalse(util.valid_path("/invalid/\r/path/"))

    def test_line_feed(self):
        """Check that a line feed character is rejected"""
        self.assertFalse(util.valid_path("/invalid/\n/path/"))


if __name__ == '__main__':
    unittest.main()

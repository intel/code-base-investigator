# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import unittest
from pathlib import Path

import codebasin.source as source


class TestSource(unittest.TestCase):
    """
    Test functionality in the source module.
    """

    def test_is_source_file_string(self):
        """Check source file identification for string filenames"""
        self.assertTrue(source.is_source_file("file.cpp"))
        self.assertTrue(source.is_source_file("/path/to/file.cpp"))
        self.assertFalse(source.is_source_file("file.o"))
        self.assertFalse(source.is_source_file("/path/to/file.o"))

    def test_is_source_file_path(self):
        """Check source file identification for Path filenames"""
        self.assertTrue(source.is_source_file(Path("file.cpp")))
        self.assertTrue(source.is_source_file(Path("/path/to/file.cpp")))
        self.assertFalse(source.is_source_file(Path("file.o")))
        self.assertFalse(source.is_source_file(Path("/path/to/file.o")))

    def test_is_source_types(self):
        """Check type validation for is_source"""
        with self.assertRaises(TypeError):
            source.is_source_file(1)


if __name__ == "__main__":
    unittest.main()

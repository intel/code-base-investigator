# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import json
import tempfile
import unittest

from codebasin import CompilationDatabase, CompileCommand


class TestCompilationDatabase(unittest.TestCase):
    """
    Test CompileDatabase class.
    """

    def setUp(self):
        self.commands = [
            CompileCommand("foo.o", command="c++ -o foo.o foo.c"),
            CompileCommand("bar.o", command="c++ -o bar.o bar.c"),
        ]
        self.valid_json = [
            {
                "arguments": ["gcc", "-c", "-o", "output", "test.cpp"],
                "directory": "/path/containing/source/files/",
                "file": "test.cpp",
            },
        ]
        self.invalid_json = [
            {
                "arguments": ["gcc", "-c", "-o", "output", "test.cpp"],
                "directory": ["not", "a", "directory"],
                "file": "test.cpp",
            },
        ]

    def test_constructor(self):
        """Check commands are stored correctly"""
        db = CompilationDatabase(self.commands)
        self.assertEqual(self.commands, db.commands)

    def test_iterator(self):
        """Check implementation of __iter__"""
        db = CompilationDatabase(self.commands)
        commands = [c for c in db]
        self.assertEqual(self.commands, commands)

    def test_from_json(self):
        """Check conversion from JSON"""
        db = CompilationDatabase.from_json(self.valid_json)
        commands = [CompileCommand.from_json(self.valid_json[0])]
        self.assertEqual(commands, db.commands)

        with self.assertRaises(ValueError):
            _ = CompilationDatabase.from_json(self.invalid_json)

    def test_from_file(self):
        """Check conversion from file"""
        with tempfile.NamedTemporaryFile(mode="w", delete_on_close=False) as f:
            json.dump(self.valid_json, f)
            f.close()
            db = CompilationDatabase.from_file(f.name)
        commands = [CompileCommand.from_json(self.valid_json[0])]
        self.assertEqual(commands, db.commands)

        with tempfile.NamedTemporaryFile(mode="w", delete_on_close=False) as f:
            json.dump(self.invalid_json, f)
            f.close()
            with self.assertRaises(ValueError):
                _ = CompilationDatabase.from_file(f.name)


if __name__ == "__main__":
    unittest.main()

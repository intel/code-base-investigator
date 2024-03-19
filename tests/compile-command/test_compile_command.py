# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import unittest

from codebasin import CompileCommand


class TestCompileCommand(unittest.TestCase):
    """
    Test CompileCommand class.
    """

    def test_commands_and_arguments(self):
        """Check commands and arguments are not both None"""

        with self.assertRaises(ValueError):
            CompileCommand("file.cpp", command=None, arguments=None)

        with self.assertRaises(ValueError):
            instance = {
                "file": "file.cpp",
            }
            CompileCommand.from_json(instance)

    def test_command_to_arguments(self):
        """Check commands convert to arguments"""
        command = CompileCommand("file.cpp", command="c++ file.cpp")
        self.assertEqual(command.arguments, ["c++", "file.cpp"])

        instance = {
            "file": "file.cpp",
            "command": "c++ file.cpp",
        }
        command = CompileCommand.from_json(instance)
        self.assertEqual(command.arguments, ["c++", "file.cpp"])

    def test_arguments_to_command(self):
        """Check arguments convert to command"""
        command = CompileCommand("file.cpp", arguments=["c++", "file.cpp"])
        self.assertEqual(str(command), "c++ file.cpp")

        instance = {
            "file": "file.cpp",
            "arguments": [
                "c++",
                "file.cpp",
            ],
        }
        command = CompileCommand.from_json(instance)
        self.assertEqual(str(command), "c++ file.cpp")

    def test_empty_command(self):
        """Check empty commands are not supported"""
        command = CompileCommand("file.cpp", command="")
        self.assertFalse(command.is_supported())

    def test_link_command(self):
        """Check link commands are not supported"""
        command = CompileCommand("file.o", command="c++ -o a.out file.o")
        self.assertFalse(command.is_supported())

    def test_valid_command(self):
        """Check valid commands are supported"""
        command = CompileCommand("file.cpp", command="c++ file.cpp")
        self.assertTrue(command.is_supported())


if __name__ == "__main__":
    unittest.main()

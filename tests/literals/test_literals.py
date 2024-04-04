# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os
import unittest

from codebasin import finder, preprocessor
from codebasin.walkers.platform_mapper import PlatformMapper


class TestLiterals(unittest.TestCase):
    """
    Simple test of C-style literal handling.
    e.g. 0x0ULL, 0b11
    """

    def setUp(self):
        self.rootdir = "./tests/literals/"
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {frozenset(["CPU", "GPU"]): 9}

    def test_literals(self):
        """literals/literals.yaml"""
        codebase = {
            "files": [
                os.path.realpath(os.path.join(self.rootdir, "main.cpp")),
            ],
            "platforms": ["CPU", "GPU"],
            "exclude_files": set(),
            "exclude_patterns": [],
            "rootdir": self.rootdir,
        }
        configuration = {
            "CPU": [
                {
                    "file": codebase["files"][0],
                    "defines": ["USE_CPU"],
                    "include_paths": [],
                    "include_files": [],
                },
            ],
            "GPU": [
                {
                    "file": codebase["files"][0],
                    "defines": ["USE_GPU"],
                    "include_paths": [],
                    "include_files": [],
                },
            ],
        }
        state = finder.find(self.rootdir, codebase, configuration)
        mapper = PlatformMapper(codebase)
        setmap = mapper.walk(state)
        self.assertDictEqual(
            setmap,
            self.expected_setmap,
            "Mismatch in setmap",
        )

    def test_strings(self):
        expected_str = r'"L + 2-2 \"\\\" \\n\""'
        tokens = preprocessor.Lexer(expected_str).tokenize()
        expected = preprocessor.StringConstant(
            "Unknown",
            "Unknown",
            False,
            r"L + 2-2 \"\\\" \\n\"",
        )
        self.assertEqual(tokens[0].token, expected.token)


if __name__ == "__main__":
    unittest.main()

# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import unittest
from pathlib import Path

import numpy as np

from codebasin import CodeBase, finder, preprocessor


class TestLiterals(unittest.TestCase):
    """
    Simple test of C-style literal handling.
    e.g. 0x0ULL, 0b11
    """

    def setUp(self):
        self.rootdir = Path(__file__).parent.resolve()
        logging.disable()

        self.expected_setmap = {frozenset(["CPU", "GPU"]): 9}

    def test_literals(self):
        """literals/literals.yaml"""
        codebase = CodeBase(self.rootdir)
        configuration = {
            "CPU": [
                {
                    "file": str(self.rootdir / "main.cpp"),
                    "defines": ["USE_CPU"],
                    "include_paths": [],
                    "include_files": [],
                },
            ],
            "GPU": [
                {
                    "file": str(self.rootdir / "main.cpp"),
                    "defines": ["USE_GPU"],
                    "include_paths": [],
                    "include_files": [],
                },
            ],
        }
        state = finder.find(self.rootdir, codebase, configuration)
        setmap = state.get_setmap(codebase)
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

    def test_long_constants(self):
        tokens = preprocessor.Lexer("0xFFFFFFFFFFFFFFFFULL").tokenize()
        term = preprocessor.ExpressionEvaluator(tokens).term()
        self.assertEqual(term, np.uint64(int("0xFFFFFFFFFFFFFFFF", 16)))


if __name__ == "__main__":
    unittest.main()

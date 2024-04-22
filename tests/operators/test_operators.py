# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os
import unittest

from codebasin import finder, platform, preprocessor
from codebasin.walkers.platform_mapper import PlatformMapper


class TestOperators(unittest.TestCase):
    """
    Simple test of ability to recognize different operators when used
    within directives
    """

    def setUp(self):
        self.rootdir = "./tests/operators/"
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {frozenset(["CPU", "GPU"]): 32}

    def test_operators(self):
        """operators/operators.yaml"""
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
                    "defines": ["CPU"],
                    "include_paths": [],
                    "include_files": [],
                },
            ],
            "GPU": [
                {
                    "file": codebase["files"][0],
                    "defines": ["GPU"],
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

    def test_paths(self):
        input_str = r"FUNCTION(looks/2like/a/path/with_/bad%%identifiers)"
        tokens = preprocessor.Lexer(input_str).tokenize()
        p = platform.Platform("Test", self.rootdir)
        macro = preprocessor.macro_from_definition_string("FUNCTION(x)=#x")
        p._definitions = {macro.name: macro}
        _ = preprocessor.MacroExpander(p).expand(tokens)


if __name__ == "__main__":
    unittest.main()

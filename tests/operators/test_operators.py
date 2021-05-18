# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import unittest
import logging
from codebasin import config, finder, preprocessor, platform
from codebasin.walkers.platform_mapper import PlatformMapper

class TestExampleFile(unittest.TestCase):
    """
    Simple test of ability to recognize different operators when used
    within directives
    """

    def setUp(self):
        self.rootdir = "./tests/operators/"
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {frozenset(['CPU', 'GPU']): 32}

    def test_yaml(self):
        """operators/operators.yaml"""
        codebase, configuration = config.load("./tests/operators/operators.yaml", self.rootdir)
        state = finder.find(self.rootdir, codebase, configuration)
        mapper = PlatformMapper(codebase)
        setmap = mapper.walk(state)
        self.assertDictEqual(setmap, self.expected_setmap, "Mismatch in setmap")

    def test_paths(self):
        input_str = r'FUNCTION(looks/2like/a/path/with_/bad%%identifiers)'
        tokens = preprocessor.Lexer(input_str).tokenize()
        p = platform.Platform("Test", self.rootdir)
        macro = preprocessor.macro_from_definition_string("FUNCTION(x)=#x")
        p._definitions = {macro.name : macro }
        exp = preprocessor.MacroExpander(p).expand(tokens)

if __name__ == '__main__':
    unittest.main()

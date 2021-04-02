# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import unittest
import logging
from codebasin import config, finder, walkers, preprocessor, platform


class TestExampleFile(unittest.TestCase):
    """
    Simple test to handle macro expansion
    """

    def setUp(self):
        self.rootdir = "./tests/macro_expansion/"
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {frozenset([]): 14,
                                frozenset(['CPU', 'GPU']): 258,
                                frozenset(['GPU']): 2,
                                frozenset(['CPU']): 3}

    def test_yaml(self):
        """macro_expansion/macro_expansion.yaml"""
        codebase, configuration = config.load(
            "./tests/macro_expansion/macro_expansion.yaml", self.rootdir)
        state = finder.find(self.rootdir, codebase, configuration)
        mapper = walkers.PlatformMapper(codebase)
        setmap = mapper.walk(state)
        self.assertDictEqual(setmap, self.expected_setmap, "Mismatch in setmap")

    def test_variadic(self):
        """variadic macros"""

        expected_expansion = [preprocessor.Identifier("Unknown", 0, False, "fprintf"),
                              preprocessor.Punctuator("Unknown", 0, False, "("),
                              preprocessor.Identifier("Unknown", 0, False, "stderr"),
                              preprocessor.Punctuator("Unknown", 0, False, ","),
                              preprocessor.StringConstant("Unknown", 0, True, "%d, %f, %e"),
                              preprocessor.Punctuator("Unknown", 0, False, ","),
                              preprocessor.Identifier("Unknown", 0, True, "a"),
                              preprocessor.Punctuator("Unknown", 0, False, ","),
                              preprocessor.Identifier("Unknown", 0, True, "b"),
                              preprocessor.Punctuator("Unknown", 0, False, ","),
                              preprocessor.Identifier("Unknown", 0, True, "c"),
                              preprocessor.Punctuator("Unknown", 0, False, ")")]

        for def_string in [
            "eprintf(...)=fprintf(stderr, __VA_ARGS__)",
                "eprintf(args...)=fprintf(stderr, args)"]:
            macro = preprocessor.macro_from_definition_string(def_string)
            tokens = preprocessor.Lexer("eprintf(\"%d, %f, %e\", a, b, c)").tokenize()
            p = platform.Platform("Test", self.rootdir)
            p._definitions = {macro.name: macro}
            expanded_tokens = preprocessor.MacroExpander(tokens,p).expand()
            self.assertTrue(len(expanded_tokens) == len(expected_expansion))
            for i in range(len(expected_expansion)):
                self.assertEqual(expanded_tokens[i].token, expected_expansion[i].token)

    def test_self_reference_macros_1(self):
        """Self referencing macros test 1"""

        expected_expansion = [preprocessor.Punctuator('Unknown', 4, False, '('),
                              preprocessor.NumericalConstant('Unknown', 5, False, '4'),
                              preprocessor.Operator('Unknown', 7, True, '+'),
                              preprocessor.Identifier('Unknown', 9, True, 'FOO'),
                              preprocessor.Punctuator('Unknown', 12, False, ')')]

        def_string = 'FOO=(4 + FOO)'
        macro = preprocessor.macro_from_definition_string(def_string)
        tokens = preprocessor.Lexer("FOO").tokenize()
        p = platform.Platform("Test", self.rootdir)
        p._definitions = {macro.name: macro}
        expanded_tokens = preprocessor.MacroExpander(tokens,p).expand()
        self.assertTrue(len(expanded_tokens) == len(expected_expansion))
        for i in range(len(expected_expansion)):
            self.assertEqual(expanded_tokens[i].line, expected_expansion[i].line)
            self.assertEqual(expanded_tokens[i].col, expected_expansion[i].col)
            self.assertEqual(expanded_tokens[i].prev_white, expected_expansion[i].prev_white)
            self.assertEqual(expanded_tokens[i].token, expected_expansion[i].token)

    def test_self_reference_macros_2(self):
        """Self referencing macros test 2"""

        expected_expansion = [preprocessor.Identifier('Unknown', 4, False, 'FOO')]

        def_string = 'FOO=FOO'
        macro = preprocessor.macro_from_definition_string(def_string)
        tokens = preprocessor.Lexer("FOO").tokenize()
        p = platform.Platform("Test", self.rootdir)
        p._definitions = {macro.name: macro}
        expanded_tokens = preprocessor.MacroExpander(tokens,p).expand()
        self.assertTrue(len(expanded_tokens) == len(expected_expansion))
        for i in range(len(expected_expansion)):
            self.assertEqual(expanded_tokens[i].line, expected_expansion[i].line)
            self.assertEqual(expanded_tokens[i].col, expected_expansion[i].col)
            self.assertEqual(expanded_tokens[i].prev_white, expected_expansion[i].prev_white)
            self.assertEqual(expanded_tokens[i].token, expected_expansion[i].token)

    def test_indirect_self_reference_macros(self):
        """ Indirect self referencing macros test"""

        x_expected_expansion = [preprocessor.Punctuator('Unknown', 2, False, '('),
                                preprocessor.NumericalConstant('Unknown', 3, False, '4'),
                                preprocessor.Operator('Unknown', 5, True, '+'),
                                preprocessor.Punctuator('Unknown', 2, False, '('),
                                preprocessor.NumericalConstant('Unknown', 3, False, '2'),
                                preprocessor.Operator('Unknown', 5, True, '*'),
                                preprocessor.Identifier('Unknown', 7, True, 'x'),
                                preprocessor.Punctuator('Unknown', 8, False, ')'),
                                preprocessor.Punctuator('Unknown', 8, False, ')')]

        y_expected_expansion = [preprocessor.Punctuator('Unknown', 2, False, '('),
                                preprocessor.NumericalConstant('Unknown', 3, False, '2'),
                                preprocessor.Operator('Unknown', 5, True, '*'),
                                preprocessor.Punctuator('Unknown', 2, False, '('),
                                preprocessor.NumericalConstant('Unknown', 3, False, '4'),
                                preprocessor.Operator('Unknown', 5, True, '+'),
                                preprocessor.Identifier('Unknown', 7, True, 'y'),
                                preprocessor.Punctuator('Unknown', 8, False, ')'),
                                preprocessor.Punctuator('Unknown', 8, False, ')')]

        x_string = 'x=(4 + y)'
        x_macro = preprocessor.macro_from_definition_string(x_string)
        y_string = 'y=(2 * x)'
        y_macro = preprocessor.macro_from_definition_string(y_string)

        x_tokens = preprocessor.Lexer("x").tokenize()
        y_tokens = preprocessor.Lexer("y").tokenize()

        p = platform.Platform("Test", self.rootdir)
        p._definitions = {x_macro.name: x_macro, y_macro.name: y_macro}

        x_expanded_tokens = preprocessor.MacroExpander(x_tokens,p).expand()

        y_expanded_tokens = preprocessor.MacroExpander(y_tokens,p).expand()

        self.assertTrue(len(x_expanded_tokens) == len(x_expected_expansion))
        for i in range(len(x_expected_expansion)):
            self.assertEqual(x_expanded_tokens[i].line, x_expected_expansion[i].line)
            self.assertEqual(x_expanded_tokens[i].col, x_expected_expansion[i].col)
            self.assertEqual(x_expanded_tokens[i].prev_white, x_expected_expansion[i].prev_white)
            self.assertEqual(x_expanded_tokens[i].token, x_expected_expansion[i].token)

        self.assertTrue(len(y_expanded_tokens) == len(y_expected_expansion))
        for i in range(len(y_expected_expansion)):
            self.assertEqual(y_expanded_tokens[i].line, y_expected_expansion[i].line)
            self.assertEqual(y_expanded_tokens[i].col, y_expected_expansion[i].col)
            self.assertEqual(y_expanded_tokens[i].prev_white, y_expected_expansion[i].prev_white)
            self.assertEqual(y_expanded_tokens[i].token, y_expected_expansion[i].token)


if __name__ == '__main__':
    unittest.main()

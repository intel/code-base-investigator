# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import unittest

from codebasin import preprocessor


class TestLexer(unittest.TestCase):
    """
    Test ability to tokenize strings correctly.
    """

    def test_character(self):
        """characters"""
        tokens = preprocessor.Lexer("'c'").tokenize()
        self.assertTrue(len(tokens) == 1)
        self.assertTrue(isinstance(tokens[0], preprocessor.CharacterConstant))

    def test_numerical(self):
        """numbers"""
        numbers = [
            "123",
            "123ul",
            "123.4",
            "123.4e+05",
            ".123",
            "0xFF",
            "0b10",
        ]
        for number in numbers:
            tokens = preprocessor.Lexer(number).tokenize()
            self.assertTrue(len(tokens) == 1)
            self.assertTrue(
                isinstance(tokens[0], preprocessor.NumericalConstant),
            )

    def test_string(self):
        """strings"""
        tokens = preprocessor.Lexer('"this is a string constant"').tokenize()
        self.assertTrue(len(tokens) == 1)
        self.assertTrue(isinstance(tokens[0], preprocessor.StringConstant))

    def test_identifier(self):
        """identifiers"""
        tokens = preprocessor.Lexer("this is a string of words").tokenize()
        self.assertTrue(len(tokens) == 6)
        self.assertTrue(
            all([isinstance(t, preprocessor.Identifier) for t in tokens]),
        )

    def test_operator(self):
        """operators"""
        operators = ["||", "&&", ">>", "<<", "!=", ">=", "<=", "==", "##"] + [
            "-",
            "+",
            "!",
            "*",
            "/",
            "|",
            "&",
            "^",
            "<",
            ">",
            "?",
            ":",
            "~",
            "#",
            "=",
            "%",
        ]
        for op in operators:
            tokens = preprocessor.Lexer(op).tokenize()
            self.assertTrue(len(tokens) == 1)
            self.assertTrue(isinstance(tokens[0], preprocessor.Operator))
            self.assertTrue(str(tokens[0].token) == op)

    def test_puncuator(self):
        """punctuators"""
        punctuators = [
            "(",
            ")",
            "{",
            "}",
            "[",
            "]",
            ",",
            ".",
            ";",
            "'",
            '"',
            "\\",
        ]
        for punc in punctuators:
            tokens = preprocessor.Lexer(punc).tokenize()
            self.assertTrue(len(tokens) == 1)
            self.assertTrue(isinstance(tokens[0], preprocessor.Punctuator))
            self.assertTrue(str(tokens[0].token) == punc)

    def test_expression(self):
        """expression"""
        tokens = preprocessor.Lexer("foo(a,b) * 124 + 'c'").tokenize()
        self.assertTrue(len(tokens) == 10)
        self.assertTrue(isinstance(tokens[0], preprocessor.Identifier))
        self.assertTrue(isinstance(tokens[1], preprocessor.Punctuator))
        self.assertTrue(isinstance(tokens[2], preprocessor.Identifier))
        self.assertTrue(isinstance(tokens[3], preprocessor.Punctuator))
        self.assertTrue(isinstance(tokens[4], preprocessor.Identifier))
        self.assertTrue(isinstance(tokens[5], preprocessor.Punctuator))
        self.assertTrue(isinstance(tokens[6], preprocessor.Operator))
        self.assertTrue(isinstance(tokens[7], preprocessor.NumericalConstant))
        self.assertTrue(isinstance(tokens[8], preprocessor.Operator))
        self.assertTrue(isinstance(tokens[9], preprocessor.CharacterConstant))

        tokens = preprocessor.Lexer(
            'a > b ? "true_string" : "false_string"',
        ).tokenize()
        self.assertTrue(len(tokens) == 7)
        self.assertTrue(isinstance(tokens[0], preprocessor.Identifier))
        self.assertTrue(isinstance(tokens[1], preprocessor.Operator))
        self.assertTrue(isinstance(tokens[2], preprocessor.Identifier))
        self.assertTrue(isinstance(tokens[3], preprocessor.Operator))
        self.assertTrue(isinstance(tokens[4], preprocessor.StringConstant))
        self.assertTrue(isinstance(tokens[5], preprocessor.Operator))
        self.assertTrue(isinstance(tokens[6], preprocessor.StringConstant))


if __name__ == "__main__":
    unittest.main()

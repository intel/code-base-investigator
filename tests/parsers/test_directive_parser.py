# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import unittest

from codebasin import preprocessor


class TestDirectiveParser(unittest.TestCase):
    """
    Test ability to parse directives correctly.
    """

    def test_define(self):
        """define"""
        tokens = preprocessor.Lexer("#define FOO").tokenize()
        node = preprocessor.DirectiveParser(tokens).parse()
        self.assertTrue(isinstance(node, preprocessor.DefineNode))
        self.assertTrue(str(node.identifier) == "FOO")
        self.assertTrue(node.args is None)
        self.assertTrue(node.value == [])

        tokens = preprocessor.Lexer("#define FOO string").tokenize()
        node = preprocessor.DirectiveParser(tokens).parse()
        self.assertTrue(isinstance(node, preprocessor.DefineNode))
        self.assertTrue(str(node.identifier) == "FOO")
        self.assertTrue(node.args is None)
        self.assertTrue(len(node.value) == 1)
        self.assertTrue(isinstance(node.value[0], preprocessor.Identifier))

        tokens = preprocessor.Lexer("#define FOO (a, b)").tokenize()
        node = preprocessor.DirectiveParser(tokens).parse()
        self.assertTrue(isinstance(node, preprocessor.DefineNode))
        self.assertTrue(str(node.identifier) == "FOO")
        self.assertTrue(node.args is None)
        self.assertTrue(len(node.value) == 5)
        self.assertTrue(isinstance(node.value[0], preprocessor.Punctuator))
        self.assertTrue(isinstance(node.value[1], preprocessor.Identifier))
        self.assertTrue(isinstance(node.value[2], preprocessor.Punctuator))
        self.assertTrue(isinstance(node.value[3], preprocessor.Identifier))
        self.assertTrue(isinstance(node.value[4], preprocessor.Punctuator))

        tokens = preprocessor.Lexer("#define FOO(a, b)").tokenize()
        node = preprocessor.DirectiveParser(tokens).parse()
        self.assertTrue(isinstance(node, preprocessor.DefineNode))
        self.assertTrue(str(node.identifier) == "FOO")
        self.assertTrue(len(node.args) == 2)
        self.assertTrue(node.value == [])

        tokens = preprocessor.Lexer("#define eprintf(...)").tokenize()
        node = preprocessor.DirectiveParser(tokens).parse()
        self.assertTrue(isinstance(node, preprocessor.DefineNode))
        self.assertTrue(str(node.identifier) == "eprintf")
        self.assertTrue(len(node.args) == 1)
        self.assertTrue(node.args[0].token == "...")

        tokens = preprocessor.Lexer("#define eprintf(args...)").tokenize()
        node = preprocessor.DirectiveParser(tokens).parse()
        self.assertTrue(isinstance(node, preprocessor.DefineNode))
        self.assertTrue(str(node.identifier) == "eprintf")
        self.assertTrue(len(node.args) == 1)
        self.assertTrue(node.args[0].token == "args...")

    def test_undef(self):
        """undef"""
        tokens = preprocessor.Lexer("#undef FOO").tokenize()
        node = preprocessor.DirectiveParser(tokens).parse()
        self.assertTrue(isinstance(node, preprocessor.UndefNode))

    def test_include(self):
        """include"""
        tokens = preprocessor.Lexer(
            "#include <path/to/system/header>",
        ).tokenize()
        node = preprocessor.DirectiveParser(tokens).parse()
        self.assertTrue(isinstance(node, preprocessor.IncludeNode))
        self.assertTrue(isinstance(node.value, preprocessor.IncludePath))
        self.assertTrue(node.value.system)

        tokens = preprocessor.Lexer(
            '#include "path/to/local/header"',
        ).tokenize()
        node = preprocessor.DirectiveParser(tokens).parse()
        self.assertTrue(isinstance(node, preprocessor.IncludeNode))
        self.assertTrue(isinstance(node.value, preprocessor.IncludePath))
        self.assertTrue(not node.value.system)

        tokens = preprocessor.Lexer("#include COMPUTED_INCLUDE").tokenize()
        node = preprocessor.DirectiveParser(tokens).parse()
        self.assertTrue(isinstance(node, preprocessor.IncludeNode))
        self.assertTrue(len(node.value) == 1)
        self.assertTrue(isinstance(node.value[0], preprocessor.Identifier))

    def test_if(self):
        """if"""
        tokens = preprocessor.Lexer("#if FOO == BAR").tokenize()
        node = preprocessor.DirectiveParser(tokens).parse()
        self.assertTrue(isinstance(node, preprocessor.IfNode))
        self.assertTrue(len(node.tokens) == 3)

    def test_ifdef(self):
        """ifdef"""
        tokens = preprocessor.Lexer("#ifdef FOO").tokenize()
        node = preprocessor.DirectiveParser(tokens).parse()
        self.assertTrue(isinstance(node, preprocessor.IfNode))
        self.assertTrue(len(node.tokens) == 4)
        self.assertTrue(isinstance(node.tokens[0], preprocessor.Identifier))
        self.assertTrue(node.tokens[0].token == "defined")

    def test_ifndef(self):
        """ifndef"""
        tokens = preprocessor.Lexer("#ifndef FOO").tokenize()
        node = preprocessor.DirectiveParser(tokens).parse()
        self.assertTrue(isinstance(node, preprocessor.IfNode))
        self.assertTrue(len(node.tokens) == 5)
        self.assertTrue(isinstance(node.tokens[0], preprocessor.Operator))
        self.assertTrue(node.tokens[0].token == "!")
        self.assertTrue(isinstance(node.tokens[1], preprocessor.Identifier))
        self.assertTrue(node.tokens[1].token == "defined")

    def test_elif(self):
        """elif"""
        tokens = preprocessor.Lexer("#elif FOO == BAR").tokenize()
        node = preprocessor.DirectiveParser(tokens).parse()
        self.assertTrue(isinstance(node, preprocessor.ElIfNode))
        self.assertTrue(len(node.tokens) == 3)

    def test_else(self):
        """else"""
        tokens = preprocessor.Lexer("#else").tokenize()
        node = preprocessor.DirectiveParser(tokens).parse()
        self.assertTrue(isinstance(node, preprocessor.ElseNode))

    def test_endif(self):
        """endif"""
        tokens = preprocessor.Lexer("#endif").tokenize()
        node = preprocessor.DirectiveParser(tokens).parse()
        self.assertTrue(isinstance(node, preprocessor.EndIfNode))

    def test_pragma(self):
        """pragma"""
        tokens = preprocessor.Lexer("#pragma anything").tokenize()
        node = preprocessor.DirectiveParser(tokens).parse()
        self.assertTrue(isinstance(node, preprocessor.PragmaNode))

    def test_unsupported(self):
        """unsupported"""
        for directive in ["#line", "#warning", "#error"]:
            tokens = preprocessor.Lexer(directive).tokenize()
            node = preprocessor.DirectiveParser(tokens).parse()
            self.assertTrue(
                isinstance(node, preprocessor.UnrecognizedDirectiveNode),
            )


if __name__ == "__main__":
    unittest.main()

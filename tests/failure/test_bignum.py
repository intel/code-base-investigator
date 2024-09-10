# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import unittest

from codebasin import preprocessor


class TestBigNum(unittest.TestCase):
    """
    Test ability to detect expressions with big numbers and prevent DoS.
    """

    def test_oversized_constant(self):
        """oversized constant"""
        with self.assertRaises(OverflowError):
            tokens = preprocessor.Lexer(
                "10000000000000000000000000000000000000",
            ).tokenize()
            preprocessor.ExpressionEvaluator(tokens).evaluate()

    def test_overflow(self):
        """integer overflow"""
        with self.assertRaises(OverflowError):
            tokens = preprocessor.Lexer(
                "0xFFFFFFFFFFFFFFFF * 0xFFFFFFFFFFFFFFFF",
            ).tokenize()
            preprocessor.ExpressionEvaluator(tokens).evaluate()

    def test_power(self):
        """integer power"""
        with self.assertRaises(preprocessor.ParseError):
            tokens = preprocessor.Lexer("* 10").tokenize()
            preprocessor.ExpressionEvaluator(tokens).evaluate()

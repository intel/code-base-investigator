# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import math
import unittest

from codebasin.report import divergence


class TestDivergence(unittest.TestCase):
    """
    Test computation of code divergence.
    """

    def setUp(self):
        logging.disable()

    def test_divergence(self):
        """Check divergence computation for simple setmap."""
        setmap = {
            frozenset(["A"]): 1,
            frozenset(["B"]): 2,
            frozenset(["A", "B"]): 3,
            frozenset([]): 4,
        }
        intersection = 3
        union = 1 + 2 + 3

        expected_divergence = intersection / union
        self.assertEqual(divergence(setmap), expected_divergence)

    def test_null_divergence(self):
        """Check divergence computation for null cases."""
        setmap = {
            frozenset(""): 0,
        }
        self.assertTrue(math.isnan(divergence(setmap)))

        setmap = {
            frozenset("A"): 1,
        }
        self.assertTrue(math.isnan(divergence(setmap)))


if __name__ == "__main__":
    unittest.main()

# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import math
import unittest

from codebasin.report import average_coverage, coverage


class TestCoverage(unittest.TestCase):
    """
    Test computation of coverage.
    """

    def setUp(self):
        logging.disable()

    def test_coverage(self):
        """Check coverage computation for simple setmap."""
        setmap = {
            frozenset(["A"]): 1,
            frozenset(["B"]): 2,
            frozenset(["A", "B"]): 3,
            frozenset([]): 4,
        }
        used_sloc = 1 + 2 + 3
        total_sloc = 1 + 2 + 3 + 4

        expected_coverage = used_sloc / total_sloc * 100.0
        self.assertEqual(coverage(setmap), expected_coverage)
        self.assertEqual(coverage(setmap, ["A", "B"]), expected_coverage)

        expected_a = (1 + 3) / total_sloc * 100.0
        self.assertEqual(coverage(setmap, ["A"]), expected_a)

        expected_b = (2 + 3) / total_sloc * 100.0
        self.assertEqual(coverage(setmap, ["B"]), expected_b)

    def test_average_coverage(self):
        """Check average coverage computation for simple setmap."""
        setmap = {
            frozenset(["A"]): 1,
            frozenset(["B"]): 2,
            frozenset(["A", "B"]): 3,
            frozenset([]): 4,
        }
        total_sloc = 1 + 2 + 3 + 4

        subset = {"A"}
        used_sloc = 1 + 3
        coverage_a = used_sloc / total_sloc * 100.0
        self.assertEqual(average_coverage(setmap, subset), coverage_a)

        subset = {"B"}
        used_sloc = 2 + 3
        coverage_b = used_sloc / total_sloc * 100.0
        self.assertEqual(average_coverage(setmap, subset), coverage_b)

        subset = {"A", "B"}
        expected_avg = (coverage_a + coverage_b) / 2
        self.assertEqual(average_coverage(setmap, subset), expected_avg)
        self.assertEqual(average_coverage(setmap), expected_avg)

    def test_null_coverage(self):
        """Check coverage computation for null cases."""
        setmap = {
            frozenset(""): 0,
        }
        self.assertTrue(math.isnan(coverage(setmap)))
        self.assertTrue(math.isnan(average_coverage(setmap)))


if __name__ == "__main__":
    unittest.main()

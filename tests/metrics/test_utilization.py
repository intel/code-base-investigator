# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import math
import unittest
import warnings

from codebasin.report import normalized_utilization, utilization


class TestUtilization(unittest.TestCase):
    """
    Test computation of code utilization.
    """

    def setUp(self):
        logging.disable()
        warnings.simplefilter("ignore", ResourceWarning)

    def test_utilization(self):
        """Check utilization computation for simple setmap."""
        setmap = {
            frozenset(["A"]): 1,
            frozenset(["B"]): 2,
            frozenset(["A", "B"]): 3,
            frozenset([]): 4,
        }
        reused_sloc = (1 * 1) + (1 * 2) + (2 * 3) + (0 * 4)
        total_sloc = 1 + 2 + 3 + 4

        expected_utilization = reused_sloc / total_sloc
        self.assertEqual(utilization(setmap), expected_utilization)

        expected_normalized = expected_utilization / 2
        self.assertEqual(normalized_utilization(setmap), expected_normalized)

        expected_normalized = expected_utilization / 4
        self.assertEqual(
            normalized_utilization(setmap, 4),
            expected_normalized,
        )

    def test_null_utilization(self):
        """Check utilization computation for null cases."""
        setmap = {
            frozenset(""): 0,
        }
        self.assertTrue(math.isnan(utilization(setmap)))
        self.assertTrue(math.isnan(normalized_utilization(setmap)))
        self.assertTrue(math.isnan(normalized_utilization(setmap, 0)))

        setmap = {
            frozenset("A"): 1,
            frozenset("B"): 1,
        }
        with self.assertRaises(ValueError):
            _ = normalized_utilization(setmap, 1)


if __name__ == "__main__":
    unittest.main()

# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import unittest
from io import StringIO

from codebasin.report import summary


class TestSummaryReport(unittest.TestCase):
    """
    Test summary report functionality.
    """

    def setUp(self):
        logging.disable()

    def test_output(self):
        """Check summary report output"""
        setmap = {
            frozenset(["X"]): 1,
            frozenset(["Y"]): 2,
            frozenset(["X", "Y"]): 3,
            frozenset([]): 6,
        }
        output = StringIO()
        summary(setmap, stream=output)
        expected = """
Summary
=======
┌────────────────┬───────┬─────────┐
│   Platform Set │   LOC │   % LOC │
├────────────────┼───────┼─────────┤
│             {} │     6 │   50.00 │
├────────────────┼───────┼─────────┤
│            {X} │     1 │    8.33 │
├────────────────┼───────┼─────────┤
│            {Y} │     2 │   16.67 │
├────────────────┼───────┼─────────┤
│         {X, Y} │     3 │   25.00 │
└────────────────┴───────┴─────────┘
Code Divergence: 0.50
Coverage (%): 50.00
Avg. Coverage (%): 37.50
Total SLOC: 12
"""
        self.assertEqual(expected, output.getvalue())


if __name__ == "__main__":
    unittest.main()

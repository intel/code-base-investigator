# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import unittest
from pathlib import Path

from codebasin import CodeBase, finder


class TestMultiLine(unittest.TestCase):
    """
    Simple test of ability to handle counting of multi-line directives
    """

    def setUp(self):
        self.rootdir = Path(__file__).parent.resolve()
        logging.disable()

        self.expected_setmap = {
            frozenset([]): 4,
            frozenset(["CPU", "GPU"]): 17,
        }

    def test_yaml(self):
        """multi_line/multi_line.yaml"""
        codebase = CodeBase(self.rootdir)
        configuration = {
            "CPU": [
                {
                    "file": str(self.rootdir / "main.cpp"),
                    "defines": ["CPU"],
                    "include_paths": [],
                    "include_files": [],
                },
            ],
            "GPU": [
                {
                    "file": str(self.rootdir / "main.cpp"),
                    "defines": ["GPU"],
                    "include_paths": [],
                    "include_files": [],
                },
            ],
        }
        state = finder.find(self.rootdir, codebase, configuration)
        setmap = state.get_setmap(codebase)
        self.assertDictEqual(
            setmap,
            self.expected_setmap,
            "Mismatch in setmap",
        )


if __name__ == "__main__":
    unittest.main()
